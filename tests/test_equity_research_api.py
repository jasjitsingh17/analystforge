"""API tests for Stage 6B POST /api/equity-research."""

from dataclasses import asdict
from typing import Any

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.equity_research import CONTROLLED_SAMPLE_INPUTS, EquityResearchInputs, run_equity_research
from backend.main import app

client = TestClient(app)
ER_URL = "/api/equity-research"


def valid_payload(**overrides: Any) -> dict[str, Any]:
    payload = asdict(CONTROLLED_SAMPLE_INPUTS)
    payload.update(overrides)
    return payload


def test_valid_request_returns_200():
    assert client.post(ER_URL, json=valid_payload()).status_code == 200


@pytest.mark.parametrize(
    "key",
    [
        "company_name",
        "ticker",
        "period",
        "revenue",
        "ebitda",
        "eps",
        "fcf",
        "market_cap",
        "enterprise_value",
        "forward_pe",
        "revenue_guidance",
        "ebitda_guidance",
        "takeaways",
        "catalysts",
        "risks",
    ],
)
def test_response_contains_required_key(key):
    assert key in client.post(ER_URL, json=valid_payload()).json()


def test_identity_fields_are_preserved():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert body["company_name"] == "Northstar Technologies plc"
    assert body["ticker"] == "NST"
    assert body["currency"] == "GBP"
    assert body["period"] == "FY2026 H1"


def test_api_results_match_equity_research_engine():
    payload = valid_payload()
    expected = run_equity_research(EquityResearchInputs(**payload))
    body = client.post(ER_URL, json=payload).json()
    assert body["revenue"]["surprise"] == pytest.approx(expected.revenue.surprise, rel=1e-12)
    assert body["ebitda"]["surprise"] == pytest.approx(expected.ebitda.surprise, rel=1e-12)
    assert body["eps"]["surprise"] == pytest.approx(expected.eps.surprise, rel=1e-12)
    assert body["fcf"]["surprise"] == pytest.approx(expected.fcf.surprise, rel=1e-12)
    assert body["market_cap"] == pytest.approx(expected.market_cap, rel=1e-12)
    assert body["enterprise_value"] == pytest.approx(expected.enterprise_value, rel=1e-12)
    assert body["forward_pe"] == pytest.approx(expected.forward_pe, rel=1e-12)


def test_default_metric_classifications_are_beats():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert body["revenue"]["classification"] == "BEAT"
    assert body["ebitda"]["classification"] == "BEAT"
    assert body["eps"]["classification"] == "BEAT"
    assert body["fcf"]["classification"] == "BEAT"


def test_default_scorecard_is_broad_based_beat():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert body["earnings_scorecard"] == "BROAD-BASED BEAT"


def test_guidance_analysis_is_exposed():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert body["revenue_guidance"]["classification"] == "RAISED"
    assert body["ebitda_guidance"]["classification"] == "RAISED"
    assert body["revenue_guidance"]["new_midpoint"] > body["revenue_guidance"]["previous_midpoint"]
    assert body["ebitda_guidance"]["new_midpoint"] > body["ebitda_guidance"]["previous_midpoint"]


def test_three_takeaways_are_returned():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert len(body["takeaways"]) == 3
    assert all(isinstance(item, str) and item for item in body["takeaways"])


def test_catalysts_and_risks_are_returned():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert len(body["catalysts"]) >= 1
    assert len(body["risks"]) >= 1


def test_margin_and_cash_conversion_metrics_are_exposed():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert body["actual_ebitda_margin"] > 0
    assert body["ebitda_margin_surprise_bps"] > 0
    assert body["fcf_conversion"] > 0


def test_valuation_multiples_are_exposed():
    body = client.post(ER_URL, json=valid_payload()).json()
    assert body["forward_pe"] > 0
    assert body["forward_ev_ebitda"] > 0
    assert body["forward_ev_revenue"] > 0


def test_custom_company_and_period_flow_through():
    body = client.post(
        ER_URL,
        json=valid_payload(company_name="Example Holdings plc", ticker="EXH", period="Q3 2026"),
    ).json()
    assert body["company_name"] == "Example Holdings plc"
    assert body["ticker"] == "EXH"
    assert body["period"] == "Q3 2026"


def test_lower_actual_revenue_can_create_a_miss():
    body = client.post(ER_URL, json=valid_payload(actual_revenue=1100.0)).json()
    assert body["revenue"]["classification"] == "MISS"
    assert body["revenue"]["surprise"] < 0


def test_changed_share_price_changes_market_cap_and_enterprise_value():
    base = client.post(ER_URL, json=valid_payload()).json()
    higher = client.post(ER_URL, json=valid_payload(share_price=30.0)).json()
    assert higher["market_cap"] > base["market_cap"]
    assert higher["enterprise_value"] > base["enterprise_value"]


def test_blank_company_name_is_rejected():
    response = client.post(ER_URL, json=valid_payload(company_name="   "))
    assert response.status_code == 422


def test_blank_ticker_is_rejected():
    response = client.post(ER_URL, json=valid_payload(ticker="   "))
    assert response.status_code == 422


def test_zero_share_price_is_rejected_by_engine():
    response = client.post(ER_URL, json=valid_payload(share_price=0))
    assert response.status_code == 422
    assert "Share price" in response.json()["detail"][0]["msg"]


def test_zero_shares_outstanding_is_rejected_by_engine():
    response = client.post(ER_URL, json=valid_payload(shares_outstanding=0))
    assert response.status_code == 422
    assert "Shares outstanding" in response.json()["detail"][0]["msg"]


def test_zero_consensus_eps_is_rejected_by_engine():
    response = client.post(ER_URL, json=valid_payload(consensus_eps=0))
    assert response.status_code == 422
    assert "consensus_eps" in response.json()["detail"][0]["msg"]


def test_inverted_revenue_guidance_is_rejected():
    response = client.post(
        ER_URL,
        json=valid_payload(new_revenue_guidance_low=5300, new_revenue_guidance_high=5200),
    )
    assert response.status_code == 422
    assert "new revenue guidance low" in response.json()["detail"][0]["msg"]


def test_missing_required_field_is_rejected():
    payload = valid_payload()
    del payload["actual_revenue"]
    response = client.post(ER_URL, json=payload)
    assert response.status_code == 422


def test_non_numeric_financial_field_is_rejected():
    response = client.post(ER_URL, json=valid_payload(actual_ebitda="not-a-number"))
    assert response.status_code == 422


def test_engine_value_error_is_normalized_to_422(monkeypatch):
    def failing_engine(inputs: EquityResearchInputs):
        raise ValueError("Simulated equity-research validation failure.")

    monkeypatch.setattr(main_module, "run_equity_research", failing_engine)
    response = client.post(ER_URL, json=valid_payload())
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Simulated equity-research validation failure."


def test_route_is_present_in_openapi_schema():
    schema = client.get("/openapi.json").json()
    assert ER_URL in schema["paths"]
    assert "post" in schema["paths"][ER_URL]


def test_health_endpoint_still_works():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
