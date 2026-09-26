"""Stage 5C dashboard and DCF sensitivity integration tests."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def valid_payload(**overrides):
    payload = {
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


def test_root_contains_professional_dcf_visual_sections():
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    for text in [
        "DCF Bridge",
        "Sensitivity Analysis",
        "Operating Forecast",
        "Cash Flow Discounting",
        "Forecast Cash Flow Detail",
    ]:
        assert text in body


def test_static_dashboard_assets_are_reachable():
    js = client.get("/static/app.js")
    css = client.get("/static/styles.css")
    assert js.status_code == 200 and "/api/dcf/sensitivity" in js.text
    assert css.status_code == 200 and ".sensitivity-table" in css.text


def test_sensitivity_returns_five_by_five_matrix_with_expected_axes():
    body = client.post("/api/dcf/sensitivity", json=valid_payload()).json()
    assert body["wacc_values"] == [0.075, 0.08, 0.085, 0.09, 0.095]
    assert body["terminal_growth_values"] == [0.015, 0.02, 0.025, 0.03, 0.035]
    assert len(body["implied_share_prices"]) == 5
    assert all(len(row) == 5 for row in body["implied_share_prices"])


def test_sensitivity_center_matches_base_dcf():
    payload = valid_payload()
    base = client.post("/api/dcf", json=payload).json()
    sensitivity = client.post("/api/dcf/sensitivity", json=payload).json()
    center = sensitivity["implied_share_prices"][2][2]
    assert center == base["implied_share_price"]
    assert sensitivity["base_implied_share_price"] == base["implied_share_price"]


def test_higher_wacc_reduces_implied_share_price_at_same_growth():
    matrix = client.post("/api/dcf/sensitivity", json=valid_payload()).json()["implied_share_prices"]
    base_growth_row = matrix[2]
    assert base_growth_row[1] > base_growth_row[2] > base_growth_row[3]


def test_higher_terminal_growth_increases_implied_share_price_at_same_wacc():
    matrix = client.post("/api/dcf/sensitivity", json=valid_payload()).json()["implied_share_prices"]
    base_wacc_column = [row[2] for row in matrix]
    assert base_wacc_column[1] < base_wacc_column[2] < base_wacc_column[3]


def test_sensitivity_marks_invalid_wacc_growth_combinations_as_null():
    body = client.post(
        "/api/dcf/sensitivity",
        json=valid_payload(wacc=0.03, terminal_growth=0.025),
    ).json()
    assert any(value is None for row in body["implied_share_prices"] for value in row)
