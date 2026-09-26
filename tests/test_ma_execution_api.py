from __future__ import annotations

import math

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.ma_api import router
from backend.ma_execution import MAExecutionInputs, run_ma_execution

app = FastAPI()
app.include_router(router)
client = TestClient(app)

DEFAULT_PAYLOAD = MAExecutionInputs().__dict__.copy()


def post(payload=None):
    return client.post("/api/ma-execution", json=payload or DEFAULT_PAYLOAD)


def test_endpoint_returns_200():
    assert post().status_code == 200


def test_endpoint_is_in_openapi():
    assert "/api/ma-execution" in client.get("/openapi.json").json()["paths"]


def test_endpoint_is_post_only():
    assert client.get("/api/ma-execution").status_code == 405


def test_default_identifiers():
    data = post().json()
    assert data["acquirer_name"] == "Apex Systems plc"
    assert data["acquirer_ticker"] == "APX"
    assert data["target_name"] == "Meridian Analytics plc"
    assert data["target_ticker"] == "MDA"
    assert data["currency"] == "GBP"


@pytest.mark.parametrize("section", [
    "transaction", "financing", "purchase_accounting", "accretion_dilution"
])
def test_response_has_core_sections(section):
    assert section in post().json()


def test_response_has_commentary_lists():
    data = post().json()
    assert len(data["key_takeaways"]) == 4
    assert len(data["execution_risks"]) == 4


@pytest.mark.parametrize("field", [
    "offer_price_per_share", "offer_premium", "equity_purchase_price",
    "target_enterprise_value", "target_ev_revenue", "target_ev_ebitda",
])
def test_transaction_matches_engine(field):
    api = post().json()["transaction"][field]
    engine = run_ma_execution().to_dict()["transaction"][field]
    assert api == pytest.approx(engine)


@pytest.mark.parametrize("field", [
    "cash_consideration", "stock_consideration", "cash_on_hand_used",
    "new_debt_raised", "new_shares_issued", "exchange_ratio",
    "existing_acquirer_ownership", "target_seller_ownership",
])
def test_financing_matches_engine(field):
    api = post().json()["financing"][field]
    engine = run_ma_execution().to_dict()["financing"][field]
    assert api == pytest.approx(engine)


@pytest.mark.parametrize("field", [
    "target_book_equity", "identifiable_intangible_write_up",
    "goodwill_created", "annual_incremental_amortization",
])
def test_purchase_accounting_matches_engine(field):
    api = post().json()["purchase_accounting"][field]
    engine = run_ma_execution().to_dict()["purchase_accounting"][field]
    assert api == pytest.approx(engine)


@pytest.mark.parametrize("field", [
    "acquirer_standalone_eps", "pro_forma_net_income",
    "pro_forma_shares_outstanding", "pro_forma_eps", "accretion_dilution",
    "after_tax_synergies", "after_tax_new_debt_interest",
    "after_tax_foregone_cash_interest", "after_tax_incremental_amortization",
    "break_even_pre_tax_synergies",
])
def test_accretion_dilution_matches_engine(field):
    api = post().json()["accretion_dilution"][field]
    engine = run_ma_execution().to_dict()["accretion_dilution"][field]
    assert api == pytest.approx(engine)


def test_classification_matches_engine():
    assert post().json()["accretion_dilution"]["classification"] == run_ma_execution().accretion_dilution.classification


def test_custom_company_names_round_trip():
    payload = DEFAULT_PAYLOAD | {
        "acquirer_name": "Northstar Holdings plc",
        "acquirer_ticker": "NSH",
        "target_name": "Orbit Data plc",
        "target_ticker": "ORB",
    }
    data = post(payload).json()
    assert (data["acquirer_name"], data["acquirer_ticker"]) == ("Northstar Holdings plc", "NSH")
    assert (data["target_name"], data["target_ticker"]) == ("Orbit Data plc", "ORB")


def test_offer_price_change_updates_premium_and_purchase_price():
    base = post().json()
    changed = post(DEFAULT_PAYLOAD | {"offer_price_per_share": 28.0}).json()
    assert changed["transaction"]["offer_premium"] > base["transaction"]["offer_premium"]
    assert changed["transaction"]["equity_purchase_price"] > base["transaction"]["equity_purchase_price"]


def test_higher_synergies_improve_accretion_dilution():
    low = post(DEFAULT_PAYLOAD | {"annual_pre_tax_synergies": 0.0}).json()
    high = post(DEFAULT_PAYLOAD | {"annual_pre_tax_synergies": 200.0}).json()
    assert high["accretion_dilution"]["accretion_dilution"] > low["accretion_dilution"]["accretion_dilution"]


def test_all_stock_deal_has_zero_new_debt_with_zero_cash_on_hand():
    payload = DEFAULT_PAYLOAD | {
        "cash_consideration_pct": 0.0,
        "stock_consideration_pct": 1.0,
        "cash_on_hand_used": 0.0,
    }
    data = post(payload).json()
    assert data["financing"]["new_debt_raised"] == pytest.approx(0.0)
    assert data["financing"]["new_shares_issued"] > 0


def test_all_cash_deal_has_zero_new_shares():
    payload = DEFAULT_PAYLOAD | {
        "cash_consideration_pct": 1.0,
        "stock_consideration_pct": 0.0,
    }
    data = post(payload).json()
    assert data["financing"]["new_shares_issued"] == pytest.approx(0.0)


@pytest.mark.parametrize("payload", [
    DEFAULT_PAYLOAD | {"cash_consideration_pct": 0.7, "stock_consideration_pct": 0.4},
    DEFAULT_PAYLOAD | {"target_share_price": 0.0},
    DEFAULT_PAYLOAD | {"offer_price_per_share": 0.0},
    DEFAULT_PAYLOAD | {"target_debt": -1.0},
    DEFAULT_PAYLOAD | {"annual_pre_tax_synergies": -1.0},
    DEFAULT_PAYLOAD | {"tax_rate": 1.0},
    DEFAULT_PAYLOAD | {"amortization_years": 0},
    DEFAULT_PAYLOAD | {"cash_on_hand_used": 2000.0},
])
def test_engine_validation_errors_are_422(payload):
    response = post(payload)
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert body["detail"][0]["type"] == "value_error"


def test_wrong_field_type_is_422():
    response = post(DEFAULT_PAYLOAD | {"offer_price_per_share": "not-a-number"})
    assert response.status_code == 422


def test_missing_fields_use_controlled_defaults():
    response = client.post("/api/ma-execution", json={})
    assert response.status_code == 200
    assert response.json()["transaction"]["offer_price_per_share"] == pytest.approx(25.0)


def test_response_is_json_serializable_and_finite():
    data = post().json()
    values = []
    for section in ("transaction", "financing", "purchase_accounting", "accretion_dilution"):
        for value in data[section].values():
            if isinstance(value, (int, float)):
                values.append(value)
    assert values
    assert all(math.isfinite(v) for v in values)
