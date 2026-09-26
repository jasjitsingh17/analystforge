"""One-page sell-side-inspired Equity Research HTML note.

Presentation only: every calculation, classification, takeaway, catalyst and risk
comes from ``backend.equity_research.EquityResearchResult``. The report is a
single self-contained A4 HTML document with inline CSS/SVG, designed for browser
viewing and Print / Save as PDF.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from math import pi

from backend.equity_research import EquityResearchResult


def _symbol(currency: str) -> str:
    return {"GBP": "£", "USD": "$", "EUR": "€"}.get(currency.upper(), f"{currency.upper()} ")


def _money(value: float, currency: str, decimals: int = 0) -> str:
    return f"{_symbol(currency)}{value:,.{decimals}f}m"


def _price(value: float, currency: str) -> str:
    return f"{_symbol(currency)}{value:,.2f}"


def _pct(value: float, decimals: int = 1, signed: bool = False) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value * 100:.{decimals}f}%"


def _bps(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.0f} bps"


def _multiple(value: float) -> str:
    return f"{value:.1f}x"


def _tone(value: float) -> str:
    return "positive" if value > 0 else "negative" if value < 0 else "neutral"


def _classification_class(value: str) -> str:
    value = value.upper()
    if value in {"BEAT", "RAISED"}:
        return "positive"
    if value in {"MISS", "LOWERED"}:
        return "negative"
    return "neutral"


def _headline(result: EquityResearchResult) -> str:
    rev_g = result.revenue_guidance.classification
    ebitda_g = result.ebitda_guidance.classification
    guidance = (
        "revenue and EBITDA guidance raised"
        if rev_g == "RAISED" and ebitda_g == "RAISED"
        else "revenue and EBITDA guidance lowered"
        if rev_g == "LOWERED" and ebitda_g == "LOWERED"
        else "guidance unchanged"
        if rev_g == "UNCHANGED" and ebitda_g == "UNCHANGED"
        else "mixed guidance revisions"
    )
    return f"{result.earnings_scorecard.title()}; {guidance}."


def _research_view(result: EquityResearchResult) -> str:
    metrics = (result.revenue, result.ebitda, result.eps, result.fcf)
    beat_count = sum(metric.classification == "BEAT" for metric in metrics)
    miss_count = sum(metric.classification == "MISS" for metric in metrics)
    if beat_count >= 3:
        return "RESULTS AHEAD"
    if miss_count >= 3:
        return "RESULTS BELOW"
    return "MIXED RESULTS"


def _metric_row(label: str, metric, currency: str, is_eps: bool = False) -> str:
    fmt = (lambda v: _price(v, currency)) if is_eps else (lambda v: _money(v, currency))
    cls = _classification_class(metric.classification)
    return (
        "<tr>"
        f"<td><strong>{escape(label)}</strong></td>"
        f"<td>{fmt(metric.prior)}</td>"
        f"<td>{fmt(metric.consensus)}</td>"
        f"<td><strong>{fmt(metric.actual)}</strong></td>"
        f"<td class='{_tone(metric.yoy_growth)}'>{_pct(metric.yoy_growth, signed=True)}</td>"
        f"<td class='{_tone(metric.surprise)}'>{_pct(metric.surprise, signed=True)}</td>"
        f"<td><span class='pill {cls}'>{escape(metric.classification)}</span></td>"
        "</tr>"
    )


def _summary_paragraph(result: EquityResearchResult) -> str:
    return (
        f"{escape(result.inputs.company_name)} reported {escape(result.inputs.period)} revenue of "
        f"{_money(result.revenue.actual, result.inputs.currency)}, {_pct(result.revenue.surprise, signed=True)} versus consensus, "
        f"while EBITDA of {_money(result.ebitda.actual, result.inputs.currency)} was {_pct(result.ebitda.surprise, signed=True)} versus expectations. "
        f"EPS was {_price(result.eps.actual, result.inputs.currency)} ({_pct(result.eps.surprise, signed=True)} versus consensus) and free cash flow was "
        f"{_money(result.fcf.actual, result.inputs.currency)}. EBITDA margin reached {_pct(result.actual_ebitda_margin)}, "
        f"{_bps(result.ebitda_margin_surprise_bps)} versus consensus."
    )


def _surprise_bar_svg(result: EquityResearchResult) -> str:
    items = [
        ("Revenue", result.revenue.surprise),
        ("EBITDA", result.ebitda.surprise),
        ("EPS", result.eps.surprise),
        ("FCF", result.fcf.surprise),
    ]
    max_abs = max(0.01, max(abs(v) for _, v in items))
    centre, maxbar = 108, 76
    rows = []
    for idx, (label, value) in enumerate(items):
        y = 15 + idx * 21
        length = abs(value) / max_abs * maxbar
        x = centre if value >= 0 else centre - length
        color = "#2b7a4b" if value >= 0 else "#b23a33"
        rows.append(f'<text x="0" y="{y+3}" font-size="8" fill="#303746">{escape(label)}</text>')
        rows.append(f'<line x1="{centre}" y1="{y-8}" x2="{centre}" y2="{y+5}" stroke="#aab3c2" stroke-width="1"/>')
        rows.append(f'<rect x="{x:.1f}" y="{y-6}" width="{length:.1f}" height="8" rx="1" fill="{color}"/>')
        rows.append(f'<text x="220" y="{y+2}" text-anchor="end" font-size="8" font-weight="700" fill="{color}">{_pct(value, signed=True)}</text>')
    return f'<svg class="chart-svg" viewBox="0 0 224 92" role="img" aria-label="Earnings surprise bar chart">{"".join(rows)}</svg>'


def _capital_structure_svg(result: EquityResearchResult) -> str:
    equity = max(result.market_cap, 0.0)
    debt = max(result.inputs.net_debt, 0.0)
    total = equity + debt
    if total <= 0:
        return '<div class="chart-note">Capital structure chart unavailable.</div>'
    equity_share = equity / total
    debt_share = debt / total
    radius = 29
    circumference = 2 * pi * radius
    equity_dash = equity_share * circumference
    debt_dash = debt_share * circumference
    return f'''
    <div class="donut-wrap">
      <svg class="donut" viewBox="0 0 100 100" role="img" aria-label="Enterprise value capital structure pie chart">
        <circle cx="50" cy="50" r="{radius}" fill="none" stroke="#3977bd" stroke-width="16" stroke-dasharray="{equity_dash:.2f} {circumference-equity_dash:.2f}" transform="rotate(-90 50 50)"/>
        <circle cx="50" cy="50" r="{radius}" fill="none" stroke="#b9c3cf" stroke-width="16" stroke-dasharray="{debt_dash:.2f} {circumference-debt_dash:.2f}" stroke-dashoffset="{-equity_dash:.2f}" transform="rotate(-90 50 50)"/>
        <text x="50" y="48" text-anchor="middle" font-size="11" font-weight="700" fill="#17314f">EV</text>
        <text x="50" y="60" text-anchor="middle" font-size="6.5" fill="#667085">{_money(result.enterprise_value, result.inputs.currency)}</text>
      </svg>
      <div class="legend-small"><span><i class="dot equity"></i>Equity {equity_share*100:.0f}%</span><span><i class="dot debt"></i>Net debt {debt_share*100:.0f}%</span></div>
    </div>'''


def _guidance_bar_svg(result: EquityResearchResult) -> str:
    vals = [
        ("Revenue", result.revenue_guidance.midpoint_revision),
        ("EBITDA", result.ebitda_guidance.midpoint_revision),
    ]
    max_abs = max(0.01, max(abs(v) for _, v in vals))
    rows = []
    for idx, (label, value) in enumerate(vals):
        y = 17 + idx * 27
        width = abs(value) / max_abs * 154
        color = "#2b7a4b" if value >= 0 else "#b23a33"
        rows.append(f'<text x="0" y="{y+2}" font-size="8" fill="#344054">{label}</text>')
        rows.append(f'<rect x="49" y="{y-7}" width="154" height="9" rx="2" fill="#eef1f5"/>')
        rows.append(f'<rect x="49" y="{y-7}" width="{width:.1f}" height="9" rx="2" fill="{color}"/>')
        rows.append(f'<text x="224" y="{y+1}" font-size="8" text-anchor="end" font-weight="700" fill="{color}">{_pct(value, signed=True)}</text>')
    return f'<svg class="wide-chart" viewBox="0 0 228 55" role="img" aria-label="Guidance revision bar chart">{"".join(rows)}</svg>'



def _growth_bar_svg(result: EquityResearchResult) -> str:
    items = [
        ("Revenue", result.revenue.yoy_growth),
        ("EBITDA", result.ebitda.yoy_growth),
        ("EPS", result.eps.yoy_growth),
        ("FCF", result.fcf.yoy_growth),
    ]
    max_abs = max(0.01, max(abs(v) for _, v in items))
    rows = []
    for idx, (label, value) in enumerate(items):
        y = 14 + idx * 19
        width = abs(value) / max_abs * 118
        color = "#3977bd" if value >= 0 else "#b23a33"
        rows.append(f'<text x="0" y="{y+2}" font-size="7.6" fill="#344054">{escape(label)}</text>')
        rows.append(f'<rect x="72" y="{y-6}" width="118" height="8" fill="#edf1f6"/>')
        rows.append(f'<rect x="72" y="{y-6}" width="{width:.1f}" height="8" fill="{color}"/>')
        rows.append(f'<text x="219" y="{y+1}" font-size="7.6" text-anchor="end" font-weight="700" fill="{color}">{_pct(value,signed=True)}</text>')
    return f'<svg class="chart-svg" viewBox="0 0 222 82" role="img" aria-label="Year-on-year operating growth bar chart">{"".join(rows)}</svg>'

def _valuation_bar_svg(result: EquityResearchResult) -> str:
    vals = [
        ("P/E", result.forward_pe),
        ("EV/EBITDA", result.forward_ev_ebitda),
        ("EV/Revenue", result.forward_ev_revenue),
        ("Net debt/EBITDA", result.net_debt_ebitda),
    ]
    maxv = max(1.0, max(v for _, v in vals))
    rows = []
    for idx, (label, value) in enumerate(vals):
        y = 14 + idx * 19
        width = max(1.5, value / maxv * 119)
        rows.append(f'<text x="0" y="{y+2}" font-size="7.6" fill="#344054">{escape(label)}</text>')
        rows.append(f'<rect x="79" y="{y-6}" width="119" height="8" fill="#edf1f6"/>')
        rows.append(f'<rect x="79" y="{y-6}" width="{width:.1f}" height="8" fill="#3977bd"/>')
        rows.append(f'<text x="219" y="{y+1}" font-size="7.6" text-anchor="end" font-weight="700" fill="#17314f">{_multiple(value)}</text>')
    return f'<svg class="chart-svg" viewBox="0 0 222 82" role="img" aria-label="Valuation multiples bar chart">{"".join(rows)}</svg>'


def _first(items, n: int) -> list[str]:
    return list(items[:n]) if hasattr(items, "__getitem__") else list(items)[:n]


def generate_equity_research_report_html(
    result: EquityResearchResult,
    *,
    generated_at: datetime | None = None,
) -> str:
    """Return a dense, one-page, sell-side-inspired A4 research note."""
    generated_at = generated_at or datetime.now()
    i = result.inputs
    c = i.currency
    rows = "".join([
        _metric_row("Revenue", result.revenue, c),
        _metric_row("EBITDA", result.ebitda, c),
        _metric_row("EPS", result.eps, c, True),
        _metric_row("Free Cash Flow", result.fcf, c),
    ])
    view = _research_view(result)
    view_class = "positive" if view == "RESULTS AHEAD" else "negative" if view == "RESULTS BELOW" else "neutral"
    catalysts = _first(result.catalysts, 2)
    risks = _first(result.risks, 2)

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(i.company_name)} — Equity Research Note</title>
<style>
:root{{--navy:#17314f;--blue:#3977bd;--pale:#f4f6f8;--line:#cfd6df;--ink:#111827;--muted:#667085;--green:#247a48;--red:#b23a33;--brown:#5a3528;--orange:#e58c3b}}
*{{box-sizing:border-box}} html,body{{margin:0;padding:0}} body{{background:#e7eaee;color:var(--ink);font-family:Georgia,"Times New Roman",serif;font-size:11px;line-height:1.28;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.toolbar{{position:sticky;top:0;z-index:20;display:flex;justify-content:center;padding:7px;background:#101828}} .toolbar button{{background:#3977bd;color:#fff;border:0;border-radius:3px;padding:7px 14px;font-family:Arial,sans-serif;font-weight:700;cursor:pointer}}
.page{{width:210mm;height:297mm;margin:10px auto;background:#fff;padding:8mm 9mm 7mm;box-shadow:0 2px 10px #0002;overflow:hidden}}
.brandline{{display:grid;grid-template-columns:1fr 175px;gap:10px;align-items:start;border-bottom:1px solid #111;padding-bottom:5px;margin-bottom:6px}} .brand{{font-size:20px;color:var(--brown);font-weight:700;letter-spacing:.01em;line-height:1.02}} .research-meta{{font-family:Arial,sans-serif;color:var(--blue);font-size:8.4px;text-align:left;font-weight:700}} .research-meta span{{display:block;color:#111;font-weight:400;margin-top:1px}}
.layout{{display:grid;grid-template-columns:minmax(0,1fr) 205px;gap:15px}} .company{{font-family:Arial,sans-serif;font-size:22px;color:#4f91ca;font-weight:700;margin:5px 0 1px}} .headline{{font-size:15.2px;line-height:1.12;margin:0 0 6px}} .summary{{font-size:10.5px;text-align:justify;margin:0 0 5px}}
.bullet-section{{margin:5px 0}} .bullet-title{{color:#1d5f9a;font-family:Arial,sans-serif;font-size:10px;font-weight:800}} .bullet-title:before{{content:"•";margin-right:4px}} .bullet-text{{margin-left:10px;text-align:justify;font-size:9.9px;line-height:1.25}} .rule{{border-top:1px solid #111;margin:5px 0}}
.sidebar{{font-family:Arial,sans-serif}} .viewbox{{border:2.5px solid var(--orange);padding:8px 8px;margin:0 0 7px}} .viewbox .view{{font-size:14px;font-weight:800;margin-bottom:4px}} .viewbox div{{margin:2px 0;font-size:8.9px}} .side-title{{font-weight:800;border-bottom:1px solid #111;padding:3px 0;margin:5px 0 3px;font-size:9.2px}} .side-card{{border-bottom:1px solid #111;padding-bottom:4px;margin-bottom:4px}}
.positive{{color:var(--green)!important}} .negative{{color:var(--red)!important}} .neutral{{color:var(--muted)!important}} .pill{{display:inline-block;border-radius:8px;padding:1px 5px;background:#eef1f5;font-family:Arial,sans-serif;font-size:6.7px;font-weight:800}} .pill.positive{{background:#e4f3e9}} .pill.negative{{background:#f9e6e5}}
.chart-svg{{width:100%;height:auto;display:block}} .wide-chart{{width:100%;height:auto}} .donut-wrap{{display:grid;grid-template-columns:69px 1fr;gap:4px;align-items:center}} .donut{{width:68px;height:68px}} .legend-small{{font-size:7px;display:flex;flex-direction:column;gap:3px}} .dot{{display:inline-block;width:6px;height:6px;margin-right:3px}} .dot.equity{{background:#3977bd}} .dot.debt{{background:#b9c3cf}}
.section-title{{font-family:Arial,sans-serif;font-size:9.4px;color:var(--navy);font-weight:800;border-bottom:1px solid #111;padding-bottom:2px;margin:6px 0 3px}} table{{border-collapse:collapse;width:100%;font-size:8.45px}} th{{font-family:Arial,sans-serif;font-size:7.5px;background:#f0f2f5;padding:3.2px;border-bottom:1px solid #9aa4b2;text-align:right}} td{{padding:3.2px;border-bottom:1px solid #e1e5ea;text-align:right}} th:first-child,td:first-child{{text-align:left}} .two{{display:grid;grid-template-columns:1fr 1fr;gap:7px}} .panel{{border:1px solid var(--line);padding:5px;break-inside:avoid}} .panel h3{{font-family:Arial,sans-serif;color:var(--navy);font-size:9px;margin:0 0 3px}} .metric-list{{display:grid;grid-template-columns:1fr auto;gap:1.5px 6px;margin:0;font-size:8.4px}} .metric-list dt{{color:#586276}} .metric-list dd{{margin:0;font-weight:700;text-align:right}} ul,ol{{margin:2px 0;padding-left:13px}} li{{margin-bottom:1.5px}}
.company-data{{display:grid;grid-template-columns:1fr auto;gap:1px 5px;font-size:8px}} .company-data div:nth-child(even){{text-align:right;font-weight:700}} .watchlist{{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}} .watch{{border-top:1px solid #111;padding-top:3px}} .watch h4{{font-family:Arial,sans-serif;font-size:8px;margin:0 0 2px;color:var(--navy)}} .watch ul{{font-size:8px;line-height:1.15;margin:0;padding-left:12px}}
.footnote{{font-size:7.3px;color:#555;margin-top:6px}} .disclosure{{font-size:7.1px;border-top:1px solid #111;margin-top:6px;padding-top:3px;line-height:1.14}} .source-line{{display:flex;justify-content:space-between;gap:8px;font-size:7.1px;color:#555;margin-top:5px}}
@page{{size:A4;margin:0}} @media print{{body{{background:#fff}}.toolbar{{display:none}}.page{{margin:0;box-shadow:none;width:210mm;height:297mm}}}}
</style>
</head>
<body>
<div class="toolbar"><button onclick="window.print()">Print / Save as PDF</button></div>
<main>
<section class="page">
  <div class="brandline"><div class="brand">Financial Analyst Automation Platform</div><div class="research-meta">Equity Research<span>{generated_at:%d %B %Y}</span><span>Automated Post-Earnings Review</span></div></div>
  <div class="layout">
    <div>
      <div class="company">{escape(i.company_name)}</div>
      <div class="headline">{escape(_headline(result))}</div>
      <p class="summary">{_summary_paragraph(result)}</p>

      <div class="bullet-section"><div class="bullet-title">What the bulls may focus on</div><div class="bullet-text">{escape(result.catalysts[0])} {escape(result.catalysts[1]) if len(result.catalysts)>1 else ''}</div></div>
      <div class="bullet-section"><div class="bullet-title">What the bears may focus on</div><div class="bullet-text">{escape(result.risks[0])} {escape(result.risks[1]) if len(result.risks)>1 else ''}</div></div>
      <div class="bullet-section"><div class="bullet-title">Our read</div><div class="bullet-text">{escape(result.takeaways[0])} {escape(result.takeaways[1]) if len(result.takeaways)>1 else ''}</div></div>
      <div class="bullet-section"><div class="bullet-title">Guidance / estimates</div><div class="bullet-text">Revenue guidance is <strong>{escape(result.revenue_guidance.classification.lower())}</strong> with a midpoint revision of {_pct(result.revenue_guidance.midpoint_revision,signed=True)}; EBITDA guidance is <strong>{escape(result.ebitda_guidance.classification.lower())}</strong> with a midpoint revision of {_pct(result.ebitda_guidance.midpoint_revision,signed=True)}.</div></div>

      <div class="section-title">Earnings vs Expectations</div>
      <table><thead><tr><th>Metric</th><th>Prior</th><th>Consensus</th><th>Actual</th><th>YoY</th><th>Surprise</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>

      <div class="two" style="margin-top:5px">
        <div class="panel"><h3>Profitability &amp; Cash Conversion</h3><dl class="metric-list"><dt>Prior EBITDA margin</dt><dd>{_pct(result.prior_ebitda_margin)}</dd><dt>Consensus EBITDA margin</dt><dd>{_pct(result.consensus_ebitda_margin)}</dd><dt>Actual EBITDA margin</dt><dd>{_pct(result.actual_ebitda_margin)}</dd><dt>Margin vs consensus</dt><dd class="{_tone(result.ebitda_margin_surprise_bps)}">{_bps(result.ebitda_margin_surprise_bps)}</dd><dt>FCF / EBITDA</dt><dd>{_pct(result.fcf_conversion)}</dd></dl></div>
        <div class="panel"><h3>Guidance Revision</h3>{_guidance_bar_svg(result)}</div>
      </div>

      <div class="section-title">Forward Estimates &amp; Valuation</div>
      <table><thead><tr><th>Metric</th><th>Forward</th><th>Valuation</th></tr></thead><tbody><tr><td>Revenue</td><td>{_money(i.forward_revenue,c)}</td><td>EV / Revenue {_multiple(result.forward_ev_revenue)}</td></tr><tr><td>EBITDA</td><td>{_money(i.forward_ebitda,c)}</td><td>EV / EBITDA {_multiple(result.forward_ev_ebitda)}</td></tr><tr><td>EPS</td><td>{_price(i.forward_eps,c)}</td><td>P/E {_multiple(result.forward_pe)}</td></tr></tbody></table>

      <div class="section-title">Management Guidance</div>
      <table><thead><tr><th>Metric</th><th>Previous Range</th><th>Current Range</th><th>Midpoint Revision</th><th>View</th></tr></thead><tbody><tr><td>Revenue</td><td>{_money(result.revenue_guidance.previous_low,c)} – {_money(result.revenue_guidance.previous_high,c)}</td><td>{_money(result.revenue_guidance.new_low,c)} – {_money(result.revenue_guidance.new_high,c)}</td><td class="{_tone(result.revenue_guidance.midpoint_revision)}">{_pct(result.revenue_guidance.midpoint_revision,signed=True)}</td><td>{escape(result.revenue_guidance.classification)}</td></tr><tr><td>EBITDA</td><td>{_money(result.ebitda_guidance.previous_low,c)} – {_money(result.ebitda_guidance.previous_high,c)}</td><td>{_money(result.ebitda_guidance.new_low,c)} – {_money(result.ebitda_guidance.new_high,c)}</td><td class="{_tone(result.ebitda_guidance.midpoint_revision)}">{_pct(result.ebitda_guidance.midpoint_revision,signed=True)}</td><td>{escape(result.ebitda_guidance.classification)}</td></tr></tbody></table>

      <div class="watchlist">
        <div class="watch"><h4>Catalysts</h4><ul>{''.join(f'<li>{escape(x)}</li>' for x in catalysts)}</ul></div>
        <div class="watch"><h4>Risks</h4><ul>{''.join(f'<li>{escape(x)}</li>' for x in risks)}</ul></div>
      </div>
    </div>

    <aside class="sidebar">
      <div class="viewbox"><div class="view {view_class}">{view}</div><div><strong>{escape(i.ticker)}</strong></div><div>Price: {_price(i.share_price,c)}</div><div>Period: {escape(i.period)}</div><div>Research view: post-results</div><div>Rating: N/A — illustrative</div><div>Price target: N/A</div></div>
      <div class="side-title">Earnings Surprise</div><div class="side-card">{_surprise_bar_svg(result)}</div>
      <div class="side-title">Operating Growth</div><div class="side-card">{_growth_bar_svg(result)}</div>
      <div class="side-title">Enterprise Value Mix</div><div class="side-card">{_capital_structure_svg(result)}</div>
      <div class="side-title">Valuation Multiples</div><div class="side-card">{_valuation_bar_svg(result)}</div>
      <div class="side-title">Company Data</div><div class="company-data"><div>Price</div><div>{_price(i.share_price,c)}</div><div>Market Cap</div><div>{_money(result.market_cap,c)}</div><div>Enterprise Value</div><div>{_money(result.enterprise_value,c)}</div><div>Shares Out.</div><div>{i.shares_outstanding:,.0f}m</div><div>Net Debt</div><div>{_money(i.net_debt,c)}</div><div>Forward P/E</div><div>{_multiple(result.forward_pe)}</div><div>EV / EBITDA</div><div>{_multiple(result.forward_ev_ebitda)}</div><div>EV / Revenue</div><div>{_multiple(result.forward_ev_revenue)}</div></div>
    </aside>
  </div>
  <div class="source-line"><span>Source: controlled sample company data, controlled consensus and Financial Analyst Automation Platform calculations.</span><span>Generated {generated_at:%d %b %Y %H:%M}</span></div>
  <div class="disclosure"><strong>Important disclosure:</strong> Illustrative automated research note using controlled sample data for a fictional issuer. No live market data, broker consensus, investment rating or price target is used. This document is for demonstration only and is not investment advice.</div>
</section>
</main></body></html>'''
