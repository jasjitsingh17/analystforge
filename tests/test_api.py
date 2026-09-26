"""API tests for POST /api/dcf.

These tests check API behaviour only: status codes, response shape, request
validation and error handling. Financial calculations are tested in
tests/test_dcf.py and are deliberately not re-implemented here.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.dcf import DCFInputs, run_dcf
from backend.main import app

client = TestClient(app)

DCF_URL = "/api/dcf"

FORECAST_ROW_KEYS = {
    "year", "revenue", "ebitda", "depreciation_amortization", "ebit", "taxes",
    "nopat", "capex", "change_in_nwc", "ufcf", "discount_factor", "pv_ufcf",
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def valid_payload(**overrides: Any) -> dict[str, Any]:
    """A valid request body, optionally overriding individual fields."""
    payload: dict[str, Any] = {
        "company_name": "Apple Inc.",
        "ticker": "AAPL",
        "share_price": 255,
        "forecast_years": 5,
        "revenue_growth": 0.08,
        "ebitda_margin": 0.33,
        "tax_rate": 0.16,
        "wacc": 0.085,
        "terminal_growth": 0.025,
        "net_debt": 50000,
        "shares_outstanding": 15000,
    }
    payload.update(overrides)
    return payload


def payload_without(field: str) -> dict[str, Any]:
    payload = valid_payload()
    del payload[field]
    return payload


def assert_rejected_for(response: Any, field: str) -> None:
    """Assert an HTTP 422 whose error details point at the given field."""
    assert response.status_code == 422
    locations = [
        str(part) for error in response.json()["detail"] for part in error["loc"]
    ]
    assert field in locations


# --------------------------------------------------------------------------
# Valid request
# --------------------------------------------------------------------------


def test_valid_request_returns_200():
    response = client.post(DCF_URL, json=valid_payload())
    assert response.status_code == 200


@pytest.mark.parametrize(
    "key",
    ["enterprise_value", "equity_value", "implied_share_price", "forecast", "terminal_value"],
)
def test_response_contains_key(key):
    body = client.post(DCF_URL, json=valid_payload()).json()
    assert key in body


def test_response_echoes_request_identity_fields():
    body = client.post(DCF_URL, json=valid_payload()).json()
    assert body["company_name"] == "Apple Inc."
    assert body["ticker"] == "AAPL"
    assert body["current_share_price"] == 255
    assert body["forecast_years"] == 5
    assert body["net_debt"] == 50000
    assert body["shares_outstanding"] == 15000


def test_forecast_has_one_complete_row_per_forecast_year():
    body = client.post(DCF_URL, json=valid_payload(forecast_years=3)).json()
    assert [row["year"] for row in body["forecast"]] == [1, 2, 3]
    for row in body["forecast"]:
        assert set(row) == FORECAST_ROW_KEYS


def test_response_values_come_from_the_dcf_engine():
    # Wiring check: the API must return what run_dcf() returns for the same
    # inputs. The expected numbers come from the engine, not from formulas here.
    payload = valid_payload()
    engine_result = run_dcf(DCFInputs(**payload))
    body = client.post(DCF_URL, json=payload).json()

    assert body["enterprise_value"] == pytest.approx(engine_result.enterprise_value, rel=1e-12)
    assert body["equity_value"] == pytest.approx(engine_result.equity_value, rel=1e-12)
    assert body["terminal_value"] == pytest.approx(engine_result.terminal_value, rel=1e-12)
    assert body["implied_share_price"] == pytest.approx(
        engine_result.implied_share_price, rel=1e-12
    )
    assert body["upside_downside"] == pytest.approx(engine_result.upside_downside, rel=1e-12)
    assert [row["ufcf"] for row in body["forecast"]] == pytest.approx(
        engine_result.ufcf, rel=1e-12
    )


# --------------------------------------------------------------------------
# Text fields
# --------------------------------------------------------------------------


def test_missing_company_name_is_rejected():
    response = client.post(DCF_URL, json=payload_without("company_name"))
    assert_rejected_for(response, "company_name")


@pytest.mark.parametrize("company_name", ["", "   "])
def test_blank_company_name_is_rejected(company_name):
    response = client.post(DCF_URL, json=valid_payload(company_name=company_name))
    assert_rejected_for(response, "company_name")


def test_missing_ticker_is_rejected():
    response = client.post(DCF_URL, json=payload_without("ticker"))
    assert_rejected_for(response, "ticker")


@pytest.mark.parametrize("ticker", ["", "   "])
def test_blank_ticker_is_rejected(ticker):
    response = client.post(DCF_URL, json=valid_payload(ticker=ticker))
    assert_rejected_for(response, "ticker")


# --------------------------------------------------------------------------
# Numeric fields
# --------------------------------------------------------------------------


@pytest.mark.parametrize("share_price", [-255, 0])
def test_non_positive_share_price_is_rejected(share_price):
    response = client.post(DCF_URL, json=valid_payload(share_price=share_price))
    assert_rejected_for(response, "share_price")


@pytest.mark.parametrize("shares_outstanding", [0, -15000])
def test_non_positive_shares_outstanding_is_rejected(shares_outstanding):
    response = client.post(DCF_URL, json=valid_payload(shares_outstanding=shares_outstanding))
    assert_rejected_for(response, "shares_outstanding")


@pytest.mark.parametrize("forecast_years", [-1, 0])
def test_non_positive_forecast_years_are_rejected(forecast_years):
    response = client.post(DCF_URL, json=valid_payload(forecast_years=forecast_years))
    assert_rejected_for(response, "forecast_years")


@pytest.mark.parametrize("forecast_years", [2.5, 5.0, "5", "five"])
def test_non_integer_forecast_years_are_rejected(forecast_years):
    response = client.post(DCF_URL, json=valid_payload(forecast_years=forecast_years))
    assert_rejected_for(response, "forecast_years")


@pytest.mark.parametrize("tax_rate", [-0.01, 1.01])
def test_invalid_tax_rate_is_rejected(tax_rate):
    response = client.post(DCF_URL, json=valid_payload(tax_rate=tax_rate))
    assert_rejected_for(response, "tax_rate")


@pytest.mark.parametrize("wacc", [0, -0.05])
def test_non_positive_wacc_is_rejected(wacc):
    response = client.post(DCF_URL, json=valid_payload(wacc=wacc))
    assert_rejected_for(response, "wacc")


def test_negative_terminal_growth_is_rejected():
    response = client.post(DCF_URL, json=valid_payload(terminal_growth=-0.01))
    assert_rejected_for(response, "terminal_growth")


@pytest.mark.parametrize("wacc", [0.02, 0.025])  # below and equal to growth
def test_wacc_not_above_terminal_growth_is_rejected(wacc):
    response = client.post(DCF_URL, json=valid_payload(wacc=wacc, terminal_growth=0.025))
    assert response.status_code == 422
    message = response.json()["detail"][0]["msg"]
    assert "WACC must be greater than terminal growth" in message


# --------------------------------------------------------------------------
# Engine errors are converted, not crashed
# --------------------------------------------------------------------------


def test_engine_value_error_is_returned_as_422(monkeypatch):
    def failing_run_dcf(inputs: DCFInputs) -> None:
        raise ValueError("Simulated engine validation failure.")

    monkeypatch.setattr(main_module, "run_dcf", failing_run_dcf)

    response = client.post(DCF_URL, json=valid_payload())

    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Simulated engine validation failure."