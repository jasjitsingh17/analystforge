from __future__ import annotations

from pathlib import Path
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.ma_api as ma_api
from backend.ma_api import router

APP = FastAPI()
APP.include_router(router)
CLIENT = TestClient(APP)

DEFAULT_PAYLOAD = {
    "acquirer_name": "Apex Systems plc",
    "acquirer_ticker": "APX",
    "target_name": "Meridian Analytics plc",
    "target_ticker": "MDA",
    "currency": "GBP",
    "acquirer_share_price": 40,
    "acquirer_shares_outstanding": 250,
    "acquirer_net_income": 600,
    "target_share_price": 20,
    "target_shares_outstanding": 100,
    "target_net_income": 120,
    "target_ltm_revenue": 1500,
    "target_ltm_ebitda": 250,
    "target_debt": 500,
    "target_cash": 200,
    "target_book_equity": 900,
    "offer_price_per_share": 25,
    "cash_consideration_pct": 0.5,
    "stock_consideration_pct": 0.5,
    "cash_on_hand_used": 500,
    "new_debt_interest_rate": 0.055,
    "cash_interest_rate": 0.02,
    "tax_rate": 0.25,
    "annual_pre_tax_synergies": 100,
    "identifiable_intangible_write_up": 300,
    "amortization_years": 10,
}


def test_excel_route_is_in_openapi():
    assert "/api/ma-execution/excel" in APP.openapi()["paths"]


def test_json_ma_route_is_preserved():
    assert "/api/ma-execution" in APP.openapi()["paths"]


def test_excel_endpoint_returns_xlsx(tmp_path, monkeypatch):
    monkeypatch.setattr(ma_api, "OUTPUTS_DIR", tmp_path)
    response = CLIENT.post("/api/ma-execution/excel", json=DEFAULT_PAYLOAD)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content.startswith(b"PK")


def test_excel_endpoint_uses_deal_tickers_in_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(ma_api, "OUTPUTS_DIR", tmp_path)
    response = CLIENT.post("/api/ma-execution/excel", json=DEFAULT_PAYLOAD)
    disposition = response.headers["content-disposition"]
    assert "APX_MDA_Merger_Model_" in disposition
    assert ".xlsx" in disposition


def test_custom_deal_download_uses_custom_tickers(tmp_path, monkeypatch):
    monkeypatch.setattr(ma_api, "OUTPUTS_DIR", tmp_path)
    payload = dict(DEFAULT_PAYLOAD, acquirer_ticker="NST", target_ticker="VTX")
    response = CLIENT.post("/api/ma-execution/excel", json=payload)
    assert response.status_code == 200
    assert "NST_VTX_Merger_Model_" in response.headers["content-disposition"]


def test_invalid_funding_mix_returns_422(tmp_path, monkeypatch):
    monkeypatch.setattr(ma_api, "OUTPUTS_DIR", tmp_path)
    payload = dict(DEFAULT_PAYLOAD, cash_consideration_pct=0.7, stock_consideration_pct=0.4)
    response = CLIENT.post("/api/ma-execution/excel", json=payload)
    assert response.status_code == 422


def test_output_copy_is_saved_in_outputs_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(ma_api, "OUTPUTS_DIR", tmp_path)
    response = CLIENT.post("/api/ma-execution/excel", json=DEFAULT_PAYLOAD)
    assert response.status_code == 200
    assert list(tmp_path.glob("APX_MDA_Merger_Model_*.xlsx"))


def _frontend_text(name: str) -> str:
    return (Path(__file__).parents[1] / "frontend" / name).read_text(encoding="utf-8")


def test_frontend_has_download_merger_model_button():
    html = _frontend_text("index.html")
    assert 'id="download-ma-excel"' in html
    assert "Download Merger Model" in html


def test_download_button_starts_disabled():
    html = _frontend_text("index.html")
    button = re.search(
        r'<button\b(?=[^>]*\bid=["\']download-ma-excel["\'])(?=[^>]*\bdisabled(?:=["\'][^"\']*["\'])?)[^>]*>',
        html,
        flags=re.IGNORECASE,
    )
    assert button is not None


def test_javascript_calls_ma_excel_endpoint():
    js = _frontend_text("app.js")
    assert 'fetch("/api/ma-execution/excel"' in js


def test_javascript_uses_last_successful_ma_payload():
    js = _frontend_text("app.js")
    assert "JSON.stringify(lastSuccessfulMAPayload)" in js


def test_javascript_enables_download_after_successful_analysis():
    js = _frontend_text("app.js")
    assert "maExcelButton.disabled = false" in js


def test_javascript_disables_download_when_inputs_change():
    js = _frontend_text("app.js")
    assert "maExcelButton.disabled = true" in js
    assert "Inputs changed" in js


def test_javascript_downloads_response_as_blob():
    js = _frontend_text("app.js")
    assert "response.blob()" in js
    assert "URL.createObjectURL(blob)" in js
    assert "anchor.download = filename" in js


def test_javascript_preserves_currency_symbol_fix():
    js = _frontend_text("app.js")
    assert "maCurrencySymbol(data.currency)}m unless stated otherwise" in js
    assert "${data.currency}m unless stated otherwise" not in js


def test_sales_and_trading_is_not_reintroduced():
    html = _frontend_text("index.html")
    js = _frontend_text("app.js")
    assert "Sales & Trading" not in html
    assert "market-monitor" not in js
