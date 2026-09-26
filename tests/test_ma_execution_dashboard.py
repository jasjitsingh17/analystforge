from pathlib import Path
import re

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def frontend_text(filename: str) -> str:
    return (ROOT / "frontend" / filename).read_text(encoding="utf-8")


def root_html() -> str:
    response = client.get("/")
    assert response.status_code == 200
    return response.text


def has_input_value(html: str, input_id: str, value: str) -> bool:
    pattern = rf'<input\b(?=[^>]*\bid="{re.escape(input_id)}")(?=[^>]*\bvalue="{re.escape(value)}")[^>]*>'
    return re.search(pattern, html) is not None


def has_hidden_section(html: str, section_id: str) -> bool:
    pattern = rf'<section\b(?=[^>]*\bid="{re.escape(section_id)}")(?=[^>]*\bhidden(?:=""|="hidden")?)[^>]*>'
    return re.search(pattern, html) is not None


def test_ma_execution_api_is_available():
    response = client.post("/api/ma-execution", json={})
    assert response.status_code == 200
    assert response.json()["accretion_dilution"]["classification"] == "ACCRETIVE"


def test_ma_execution_route_is_in_openapi():
    schema = client.get("/openapi.json").json()
    assert "/api/ma-execution" in schema["paths"]
    assert "post" in schema["paths"]["/api/ma-execution"]


def test_ma_tab_exists_in_public_navigation():
    html = root_html()
    assert 'id="tab-ma"' in html
    assert 'aria-controls="panel-ma"' in html
    assert "M&amp;A Execution" in html


def test_ma_panel_is_real_workflow_not_placeholder():
    html = frontend_text("index.html")
    assert 'id="panel-ma"' in html
    assert "Deal structuring, financing, purchase accounting and accretion / dilution analysis." in html
    assert "Coming" not in html[html.index('id="panel-ma"'):html.index('id="panel-er"')]


def test_sales_and_trading_does_not_return_to_navigation():
    html = frontend_text("index.html")
    assert 'id="tab-st"' not in html
    assert 'id="panel-st"' not in html
    assert "Sales &amp; Trading" not in html


def test_existing_investment_banking_tab_is_preserved():
    html = frontend_text("index.html")
    assert 'id="tab-ib"' in html
    assert 'id="panel-ib"' in html
    assert "Run DCF Valuation" in html


def test_existing_equity_research_tab_is_preserved():
    html = frontend_text("index.html")
    assert 'id="tab-er"' in html
    assert 'id="panel-er"' in html
    assert "Run Earnings Review" in html
    assert "Open Research Note" in html


def test_ma_dashboard_uses_python_engine_badge():
    html = frontend_text("index.html")
    assert "Python M&amp;A Engine" in html


def test_default_controlled_acquirer_inputs_are_present():
    html = frontend_text("index.html")
    assert has_input_value(html, "ma-acquirer-name", "Apex Systems plc")
    assert has_input_value(html, "ma-acquirer-ticker", "APX")
    assert has_input_value(html, "ma-acquirer-share-price", "40")
    assert has_input_value(html, "ma-acquirer-net-income", "600")


def test_default_controlled_target_inputs_are_present():
    html = frontend_text("index.html")
    assert has_input_value(html, "ma-target-name", "Meridian Analytics plc")
    assert has_input_value(html, "ma-target-ticker", "MDA")
    assert has_input_value(html, "ma-target-share-price", "20")
    assert has_input_value(html, "ma-target-ebitda", "250")


def test_default_transaction_inputs_are_present():
    html = frontend_text("index.html")
    assert has_input_value(html, "ma-offer-price", "25")
    assert has_input_value(html, "ma-cash-pct", "50")
    assert has_input_value(html, "ma-stock-pct", "50")
    assert has_input_value(html, "ma-synergies", "100")


def test_default_purchase_accounting_inputs_are_present():
    html = frontend_text("index.html")
    assert has_input_value(html, "ma-intangible-writeup", "300")
    assert has_input_value(html, "ma-amortization-years", "10")


def test_run_deal_analysis_button_exists():
    html = frontend_text("index.html")
    assert 'id="run-ma"' in html
    assert "Run Deal Analysis" in html


def test_ma_output_dashboard_starts_hidden():
    html = frontend_text("index.html")
    assert has_hidden_section(html, "ma-dashboard")


def test_transaction_overview_output_exists():
    html = frontend_text("index.html")
    assert 'id="ma-deal-title"' in html
    assert 'id="ma-classification"' in html
    assert 'id="ma-accretion-badge"' in html


def test_headline_transaction_metrics_exist():
    html = frontend_text("index.html")
    for field_id in [
        "ma-out-offer-price",
        "ma-out-premium",
        "ma-out-equity-value",
        "ma-out-enterprise-value",
        "ma-out-ev-ebitda",
        "ma-out-accretion",
    ]:
        assert f'id="{field_id}"' in html


def test_consideration_and_funding_visual_exists():
    html = frontend_text("index.html")
    assert "Consideration &amp; Funding" in html
    assert 'id="ma-consideration-bars"' in html
    assert 'id="ma-funding-strip"' in html


def test_pro_forma_ownership_visual_exists():
    html = frontend_text("index.html")
    assert "Pro Forma Ownership" in html
    assert 'id="ma-ownership-donut"' in html
    assert 'id="ma-existing-ownership"' in html
    assert 'id="ma-seller-ownership"' in html


def test_accretion_dilution_bridge_exists():
    html = frontend_text("index.html")
    assert "Accretion / Dilution Bridge" in html
    assert 'id="ma-standalone-eps"' in html
    assert 'id="ma-proforma-eps"' in html
    assert 'id="ma-break-even-synergies"' in html
    assert 'id="ma-earnings-bridge"' in html


def test_purchase_accounting_section_exists():
    html = frontend_text("index.html")
    assert "Purchase Accounting" in html
    assert 'id="ma-goodwill"' in html
    assert 'id="ma-amortization"' in html
    assert 'id="ma-purchase-stack"' in html


def test_deal_execution_detail_table_exists():
    html = frontend_text("index.html")
    assert "Deal Execution Detail" in html
    assert 'id="ma-deal-table-body"' in html
    assert "Interpretation" in html


def test_takeaways_and_execution_risks_exist():
    html = frontend_text("index.html")
    assert "Key Deal Takeaways" in html
    assert "Execution Risks" in html
    assert 'id="ma-takeaways"' in html
    assert 'id="ma-risks"' in html


def test_methodology_discloses_controlled_fictional_data():
    html = frontend_text("index.html")
    assert "controlled sample data for fictional companies" in html
    assert "does not constitute transaction, investment or accounting advice" in html


def test_javascript_calls_ma_execution_api():
    js = frontend_text("app.js")
    assert 'fetch("/api/ma-execution"' in js
    assert 'method: "POST"' in js
    assert '"Content-Type": "application/json"' in js


def test_javascript_converts_percentage_form_inputs_to_decimal_api_inputs():
    js = frontend_text("app.js")
    assert 'cash_consideration_pct: maNumber("ma-cash-pct") / 100' in js
    assert 'stock_consideration_pct: maNumber("ma-stock-pct") / 100' in js
    assert 'new_debt_interest_rate: maNumber("ma-new-debt-rate") / 100' in js
    assert 'tax_rate: maNumber("ma-tax-rate") / 100' in js


def test_javascript_uses_api_response_for_core_outputs():
    js = frontend_text("app.js")
    assert "data.transaction" in js
    assert "data.financing" in js
    assert "data.purchase_accounting" in js
    assert "data.accretion_dilution" in js
    assert "data.key_takeaways" in js
    assert "data.execution_risks" in js


def test_frontend_does_not_duplicate_core_ma_engine_formulas():
    js = frontend_text("app.js")
    forbidden = [
        "offer_price_per_share * target_shares_outstanding",
        "equity_purchase_price + target_debt - target_cash",
        "stock_consideration / acquirer_share_price",
        "pro_forma_net_income / pro_forma_shares",
        "annual_pre_tax_synergies * (1 - tax_rate)",
    ]
    for formula in forbidden:
        assert formula not in js


def test_javascript_hides_stale_dashboard_after_input_changes():
    js = frontend_text("app.js")
    assert 'maForm.addEventListener("input"' in js
    assert "maDashboard.hidden = true" in js
    assert "Inputs changed — run the deal analysis again" in js


def test_javascript_has_readable_validation_error_handling():
    js = frontend_text("app.js")
    assert "The M&A service returned an error" in js
    assert "error.detail" in js
    assert "Unable to connect to the M&A execution service." in js


def test_javascript_renders_accretive_dilutive_neutral_states():
    js = frontend_text("app.js")
    assert 'normalized === "accretive"' in js
    assert 'normalized === "dilutive"' in js
    assert 'return "is-neutral"' in js


def test_ma_styles_are_present():
    css = frontend_text("styles.css")
    for selector in [
        ".ma-form-grid",
        ".ma-headline-grid",
        ".ma-consideration-bars",
        ".ma-ownership-donut",
        ".ma-earnings-bridge",
        ".ma-purchase-stack",
        ".ma-commentary-grid",
    ]:
        assert selector in css


def test_ma_dashboard_is_responsive():
    css = frontend_text("styles.css")
    assert "@media (max-width: 1180px)" in css
    assert "@media (max-width: 900px)" in css
    assert "@media (max-width: 700px)" in css


def test_sales_trading_styles_are_not_reintroduced():
    css = frontend_text("styles.css")
    assert ".st-pulse-card" not in css
    assert ".st-asset-grid" not in css
    assert ".st-signal-table" not in css


def test_sales_trading_javascript_is_not_reintroduced():
    js = frontend_text("app.js")
    assert "loadMarketMonitor" not in js
    assert "stDashboard" not in js
    assert "/api/market-monitor" not in js


def test_static_assets_are_served():
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_root_page_uses_static_asset_paths():
    html = root_html()
    assert 'href="/static/styles.css"' in html
    assert 'src="/static/app.js"' in html
