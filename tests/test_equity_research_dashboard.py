"""Stage 6C integration tests for the analyst-style Equity Research dashboard.

These tests deliberately do not reproduce equity-research formulas. Numerical
expectations come from the tested Python engine through the FastAPI endpoint.
"""

from fastapi.testclient import TestClient
import pytest

from backend.main import app

client = TestClient(app)


def default_payload() -> dict[str, float | str]:
    return {
        "company_name": "Northstar Technologies plc",
        "ticker": "NST",
        "currency": "GBP",
        "period": "FY2026 H1",
        "share_price": 25.0,
        "shares_outstanding": 200.0,
        "net_debt": 600.0,
        "prior_revenue": 1100.0,
        "consensus_revenue": 1200.0,
        "actual_revenue": 1260.0,
        "prior_ebitda": 240.0,
        "consensus_ebitda": 280.0,
        "actual_ebitda": 300.0,
        "prior_eps": 0.36,
        "consensus_eps": 0.42,
        "actual_eps": 0.46,
        "prior_fcf": 170.0,
        "consensus_fcf": 195.0,
        "actual_fcf": 210.0,
        "forward_revenue": 5200.0,
        "forward_ebitda": 1100.0,
        "forward_eps": 1.60,
        "previous_revenue_guidance_low": 4900.0,
        "previous_revenue_guidance_high": 5100.0,
        "new_revenue_guidance_low": 5000.0,
        "new_revenue_guidance_high": 5200.0,
        "previous_ebitda_guidance_low": 1000.0,
        "previous_ebitda_guidance_high": 1080.0,
        "new_ebitda_guidance_low": 1050.0,
        "new_ebitda_guidance_high": 1130.0,
    }


def root_html() -> str:
    response = client.get("/")
    assert response.status_code == 200
    return response.text


def test_equity_research_tab_is_a_real_workflow_not_placeholder():
    html = root_html()
    assert 'id="er-form"' in html
    assert "Run Earnings Review" in html
    assert "Coming in Stage 6" not in html


def test_dashboard_contains_professional_research_sections():
    html = root_html()
    for title in (
        "Earnings Snapshot",
        "Earnings Surprise",
        "Profitability &amp; Cash Conversion",
        "Earnings vs Expectations",
        "Guidance Revision",
        "Valuation Snapshot",
        "Key Takeaways",
        "Catalysts",
        "Risks",
        "Methodology &amp; Limitations",
    ):
        assert title in html


def test_default_controlled_company_inputs_are_present():
    html = root_html()
    for value in (
        "Northstar Technologies plc",
        "NST",
        "FY2026 H1",
        'value="1260"',
        'value="300"',
        'value="0.46"',
        'value="210"',
    ):
        assert value in html


def test_dashboard_discloses_controlled_sample_data():
    html = root_html().lower()
    assert "controlled sample data" in html
    assert "not investment advice" in html


def test_stylesheet_is_reachable():
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert ".er-kpi-grid" in response.text
    assert ".er-guidance-wrap" in response.text


def test_javascript_is_reachable():
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert 'fetch("/api/equity-research"' in response.text


def test_javascript_renders_api_fields_instead_of_recalculating_research_logic():
    js = client.get("/static/app.js").text
    for api_field in (
        "earnings_scorecard",
        "strongest_surprise_metric",
        "ebitda_margin_surprise_bps",
        "forward_ev_ebitda",
        "revenue_guidance",
        "takeaways",
        "catalysts",
        "risks",
    ):
        assert api_field in js
    assert "run_equity_research" not in js


def test_default_api_response_drives_broad_based_beat_dashboard():
    body = client.post("/api/equity-research", json=default_payload()).json()
    assert body["earnings_scorecard"] == "BROAD-BASED BEAT"
    assert body["strongest_surprise_metric"] == "EPS"
    assert body["strongest_surprise"] == pytest.approx(0.0952380952)


@pytest.mark.parametrize("metric", ["revenue", "ebitda", "eps", "fcf"])
def test_default_snapshot_metrics_are_beats(metric):
    body = client.post("/api/equity-research", json=default_payload()).json()
    assert body[metric]["classification"] == "BEAT"
    assert body[metric]["surprise"] > 0


def test_default_profitability_metrics_are_exposed_for_dashboard():
    body = client.post("/api/equity-research", json=default_payload()).json()
    assert body["actual_ebitda_margin"] == pytest.approx(300 / 1260)
    assert body["actual_ebitda_margin"] > body["consensus_ebitda_margin"]
    assert body["ebitda_margin_surprise_bps"] > 0
    assert body["fcf_conversion"] == pytest.approx(0.70)


def test_default_guidance_is_raised_for_both_revenue_and_ebitda():
    body = client.post("/api/equity-research", json=default_payload()).json()
    assert body["revenue_guidance"]["classification"] == "RAISED"
    assert body["ebitda_guidance"]["classification"] == "RAISED"
    assert body["revenue_guidance"]["midpoint_revision"] > 0
    assert body["ebitda_guidance"]["midpoint_revision"] > 0


def test_default_valuation_snapshot_is_financially_consistent():
    body = client.post("/api/equity-research", json=default_payload()).json()
    assert body["market_cap"] == pytest.approx(5000.0)
    assert body["enterprise_value"] == pytest.approx(5600.0)
    assert body["forward_pe"] == pytest.approx(15.625)
    assert body["forward_ev_ebitda"] == pytest.approx(5600 / 1100)
    assert body["forward_ev_revenue"] == pytest.approx(5600 / 5200)


def test_commentary_sections_have_research_content():
    body = client.post("/api/equity-research", json=default_payload()).json()
    assert len(body["takeaways"]) == 3
    assert len(body["catalysts"]) == 3
    assert len(body["risks"]) == 3
    assert all(isinstance(item, str) and item for item in body["takeaways"])


def test_investment_banking_workflow_remains_present():
    html = root_html()
    assert 'id="dcf-form"' in html
    assert 'id="download-excel"' in html
    assert "DCF Bridge" in html
    assert "Sensitivity Analysis" in html

def test_sales_and_trading_removed_from_public_navigation():
    html = root_html()
    assert 'id="tab-st"' not in html
    assert 'id="panel-st"' not in html


def test_equity_research_status_is_accessible():
    html = root_html()
    assert 'id="er-status"' in html
    assert 'aria-live="polite"' in html
