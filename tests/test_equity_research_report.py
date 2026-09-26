from datetime import datetime

from fastapi.testclient import TestClient

from backend.equity_research import EquityResearchInputs, run_equity_research
from backend.equity_research_report import generate_equity_research_report_html
from backend.main import app

client = TestClient(app)
URL = "/api/equity-research/report"


def payload(**overrides):
    data = EquityResearchInputs().__dict__.copy()
    data.update(overrides)
    return data


def report():
    return generate_equity_research_report_html(run_equity_research(EquityResearchInputs()))


def test_report_generator_returns_full_html_document():
    html = report()
    assert html.startswith("<!doctype html>") and "</html>" in html


def test_report_is_print_ready_a4():
    html = report()
    assert "@page" in html and "size:A4" in html
    assert "window.print()" in html and "Print / Save as PDF" in html


def test_report_is_exactly_one_page_section():
    html = report()
    assert html.count('<section class="page">') == 1
    assert "page-break" not in html
    assert "Detailed Earnings Review" not in html


def test_report_uses_sell_side_inspired_layout():
    html = report()
    assert "Financial Analyst Automation Platform" in html
    assert "What the bulls may focus on" in html
    assert "What the bears may focus on" in html
    assert "Our read" in html
    assert "Company Data" in html


def test_report_contains_identity_fields():
    html = report()
    for text in ("Northstar Technologies plc", "NST", "FY2026 H1"):
        assert text in html


def test_report_contains_research_view_box_without_fake_rating():
    html = report()
    assert "RESULTS AHEAD" in html
    assert "Research view: post-results" in html
    assert "Rating: N/A — illustrative" in html
    assert "Price target: N/A" in html


def test_report_contains_earnings_snapshot_data():
    html = report()
    for text in ("£1,260m", "£300m", "£0.46", "£210m"):
        assert text in html


def test_report_contains_consensus_table():
    html = report()
    assert "Earnings vs Expectations" in html
    assert html.count("BEAT") >= 4
    assert "+5.0%" in html and "+9.5%" in html


def test_report_contains_inline_svg_charts():
    html = report()
    assert html.count("<svg") >= 5
    assert "Earnings surprise bar chart" in html
    assert "Year-on-year operating growth bar chart" in html
    assert "Enterprise value capital structure pie chart" in html
    assert "Guidance revision bar chart" in html
    assert "Valuation multiples bar chart" in html


def test_report_contains_pie_chart_legend():
    html = report()
    assert "Equity 89%" in html
    assert "Net debt 11%" in html


def test_report_contains_profitability_and_cash_conversion():
    html = report()
    assert "Profitability &amp; Cash Conversion" in html
    assert "23.8%" in html and "+48 bps" in html and "70.0%" in html


def test_report_contains_guidance_analysis():
    html = report()
    assert "Guidance / estimates" in html
    assert "+2.0%" in html and "+4.8%" in html



def test_report_contains_compact_management_guidance_table():
    html = report()
    assert "Management Guidance" in html
    assert "Previous Range" in html and "Current Range" in html
    assert "£4,900m – £5,100m" in html
    assert "£5,000m – £5,200m" in html

def test_report_contains_valuation_snapshot_data():
    html = report()
    for text in ("£5,000m", "£5,600m", "15.6x", "5.1x"):
        assert text in html


def test_report_contains_condensed_catalysts_and_risks_on_same_page():
    result = run_equity_research(EquityResearchInputs())
    html = generate_equity_research_report_html(result)
    assert "Catalysts" in html and "Risks" in html
    for item in result.catalysts[:2]:
        assert item in html
    for item in result.risks[:2]:
        assert item in html


def test_report_discloses_controlled_sample_and_no_rating():
    html = report()
    assert "controlled sample data" in html.lower()
    assert "fictional issuer" in html.lower()
    assert "no live market data" in html.lower()
    assert "investment rating" in html.lower()
    assert "not investment advice" in html.lower()


def test_report_timestamp_can_be_deterministic():
    html = generate_equity_research_report_html(
        run_equity_research(EquityResearchInputs()),
        generated_at=datetime(2026, 9, 25, 17, 30),
    )
    assert "25 September 2026" in html
    assert "25 Sep 2026 17:30" in html


def test_report_handles_net_cash_without_crashing():
    result = run_equity_research(EquityResearchInputs(net_debt=-200))
    html = generate_equity_research_report_html(result)
    assert "Enterprise Value Mix" in html
    assert "Net Debt" in html


def test_report_endpoint_returns_html():
    response = client.post(URL, json=payload())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Northstar Technologies plc" in response.text


def test_report_endpoint_uses_submitted_company_and_period():
    response = client.post(URL, json=payload(company_name="Atlas Systems plc", ticker="ATL", period="FY2027 Q1"))
    assert response.status_code == 200
    assert "Atlas Systems plc" in response.text and "ATL" in response.text and "FY2027 Q1" in response.text


def test_report_endpoint_preserves_financial_validation():
    assert client.post(URL, json=payload(share_price=0)).status_code == 422


def test_report_route_is_in_openapi_schema():
    paths = client.get("/openapi.json").json()["paths"]
    assert URL in paths and "post" in paths[URL]


def test_frontend_exposes_open_research_note_button():
    html = client.get("/").text
    assert 'id="open-er-report"' in html and "Open Research Note" in html


def test_frontend_javascript_calls_report_endpoint():
    js = client.get("/static/app.js").text
    assert 'fetch("/api/equity-research/report"' in js and "window.open" in js


def test_frontend_disables_report_if_inputs_change():
    js = client.get("/static/app.js").text
    assert "erReportButton.disabled = true" in js
    assert "run the earnings review again before opening or downloading research outputs" in js
