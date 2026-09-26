"""Professional Excel generator for the Equity Research workflow.

Architecture
------------
EquityResearchInputs -> run_equity_research() -> EquityResearchResult
    -> generate_equity_research_workbook() -> .xlsx

The Python engine in ``backend/equity_research.py`` remains the source of
truth.  This generator lays out raw controlled inputs, creates visible Excel
formulas for analyst calculations, and writes Python-engine reference values
into ``08_Model_Checks`` so the Excel model can reconcile back to Python.

Colour convention
-----------------
Blue   = hard-coded / user-editable input
Black  = same-sheet Excel formula
Green  = link to another worksheet
Purple = Python-engine reference value used only for reconciliation

The workbook uses controlled sample data and is not investment advice.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.worksheet import Worksheet

from backend.equity_research import EquityResearchResult

SHEET_COVER = "00_Cover"
SHEET_SUMMARY = "01_Earnings_Summary"
SHEET_HISTORICAL = "02_Historical"
SHEET_CONSENSUS = "03_Consensus_vs_Actual"
SHEET_KPIS = "04_KPIs"
SHEET_GUIDANCE = "05_Guidance"
SHEET_VALUATION = "06_Valuation"
SHEET_TAKEAWAYS = "07_Analyst_Takeaways"
SHEET_CHECKS = "08_Model_Checks"
SHEET_SOURCES = "09_Data_Sources"

SHEET_NAMES: tuple[str, ...] = (
    SHEET_COVER,
    SHEET_SUMMARY,
    SHEET_HISTORICAL,
    SHEET_CONSENSUS,
    SHEET_KPIS,
    SHEET_GUIDANCE,
    SHEET_VALUATION,
    SHEET_TAKEAWAYS,
    SHEET_CHECKS,
    SHEET_SOURCES,
)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
CHECK_TOLERANCE = 1e-6
INLINE_TOLERANCE = 0.005

# Finance-style formats: zeros as dash, negatives red in parentheses.
FMT_NUM = '#,##0;[Red](#,##0);-'
FMT_NUM1 = '#,##0.0;[Red](#,##0.0);-'
FMT_PRICE = '#,##0.00;[Red](#,##0.00);-'
FMT_EPS = '0.00;[Red](0.00);-'
FMT_PCT1 = '0.0%;[Red](0.0%);-'
FMT_PCT2 = '0.00%;[Red](0.00%);-'
FMT_BPS = '0" bps";[Red](0" bps");-'
FMT_MULTIPLE = '0.0x;[Red](0.0x);-'
FMT_CHECK = '#,##0.000000;[Red](#,##0.000000);-'

_FONT = "Arial"
_NAVY = "17365D"
_DARK_NAVY = "10253F"
_BLUE = "0000FF"
_GREEN = "008000"
_PURPLE = "7030A0"
_RED = "C00000"
_GREY = "F2F2F2"
_LIGHT_BLUE = "D9EAF7"
_LIGHT_GREEN = "E2F0D9"
_LIGHT_RED = "FCE4D6"
_LIGHT_YELLOW = "FFF2CC"
_WHITE = "FFFFFF"
_BORDER = "B7C9DE"

_THIN = Side(style="thin", color=_BORDER)
_MEDIUM = Side(style="medium", color="7F8FA4")
_BOX = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_TOP = Border(top=Side(style="thin", color="000000"))
_BOTTOM = Border(bottom=Side(style="thin", color="000000"))

SOURCE_COMMENT = (
    "Source: Controlled sample data supplied to the deterministic Python "
    "Equity Research engine. Fictional issuer; not live company or market data."
)


def _font(kind: str = "calc", *, bold: bool = False, size: int = 10, italic: bool = False) -> Font:
    color = {
        "input": _BLUE,
        "calc": "000000",
        "link": _GREEN,
        "python": _PURPLE,
        "label": "000000",
    }[kind]
    return Font(name=_FONT, size=size, bold=bold, italic=italic, color=color)


def _put(
    ws: Worksheet,
    cell: str,
    value: object,
    *,
    kind: str = "calc",
    fmt: str | None = None,
    bold: bool = False,
    size: int = 10,
    italic: bool = False,
    fill: str | None = None,
    border: Border | None = None,
    align: str | None = None,
    wrap: bool = False,
    source_comment: bool = False,
) -> None:
    c = ws[cell]
    c.value = value
    c.font = _font(kind, bold=bold, size=size, italic=italic)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    if border:
        c.border = border
    c.alignment = Alignment(
        horizontal=align,
        vertical="top" if wrap else "center",
        wrap_text=wrap,
    )
    if source_comment:
        c.comment = Comment(SOURCE_COMMENT, "Financial Analyst Automation Platform")


def _sheet_base(ws: Worksheet, *, landscape: bool = True) -> None:
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.freeze_panes = "A5"


def _title(ws: Worksheet, title: str, subtitle: str, last_col: int = 7) -> None:
    _sheet_base(ws)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    ws["A1"] = title
    ws["A1"].font = Font(name=_FONT, size=15, bold=True, color=_WHITE)
    ws["A1"].fill = PatternFill("solid", fgColor=_NAVY)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 24
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=last_col)
    ws["A2"] = subtitle
    ws["A2"].font = Font(name=_FONT, size=9, italic=True, color="595959")


def _section(ws: Worksheet, row: int, text: str, last_col: int) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    c = ws.cell(row=row, column=1)
    c.value = text
    c.fill = PatternFill("solid", fgColor=_NAVY)
    c.font = Font(name=_FONT, size=10, bold=True, color=_WHITE)
    c.alignment = Alignment(horizontal="left")


def _header(ws: Worksheet, row: int, labels: Iterable[str]) -> None:
    for col, label in enumerate(labels, start=1):
        c = ws.cell(row=row, column=col)
        c.value = label
        c.font = Font(name=_FONT, size=10, bold=True, color="000000")
        c.fill = PatternFill("solid", fgColor=_GREY)
        c.border = _BOTTOM
        c.alignment = Alignment(horizontal="left" if col == 1 else "right")


def _widths(ws: Worksheet, widths: dict[str, float]) -> None:
    for col, width in widths.items():
        ws.column_dimensions[col].width = width


def _cross(sheet: str, cell: str) -> str:
    return f"'{sheet}'!{cell}"


def _classification_fill(value: str) -> str:
    if value in {"BEAT", "RAISED"}:
        return _LIGHT_GREEN
    if value in {"MISS", "LOWERED"}:
        return _LIGHT_RED
    return _LIGHT_YELLOW


def _build_summary(ws: Worksheet, result: EquityResearchResult) -> None:
    _title(
        ws,
        "Earnings Summary",
        "Controlled post-earnings review. Blue = input; black = formula; green = cross-sheet link.",
        7,
    )
    _widths(ws, {"A": 24, "B": 16, "C": 16, "D": 16, "E": 14, "F": 14, "G": 14})

    _section(ws, 4, "Company / Reporting Information", 7)
    labels = [
        ("Company", result.inputs.company_name),
        ("Ticker", result.inputs.ticker),
        ("Currency", result.inputs.currency),
        ("Reporting Period", result.inputs.period),
    ]
    for i, (label, value) in enumerate(labels, start=5):
        _put(ws, f"A{i}", label, kind="label", bold=True)
        _put(ws, f"B{i}", value, kind="input", source_comment=True)

    _section(ws, 10, "Earnings vs Expectations", 7)
    _header(ws, 11, ["Metric", "Prior", "Consensus", "Actual", "YoY", "Surprise", "Result"])

    metric_rows = {
        "Revenue": (12, result.revenue, FMT_NUM),
        "EBITDA": (13, result.ebitda, FMT_NUM),
        "EPS": (14, result.eps, FMT_EPS),
        "Free Cash Flow": (15, result.fcf, FMT_NUM),
    }
    for name, (row, metric, fmt) in metric_rows.items():
        _put(ws, f"A{row}", name, kind="label", bold=True)
        _put(ws, f"B{row}", metric.prior, kind="input", fmt=fmt, source_comment=True)
        _put(ws, f"C{row}", metric.consensus, kind="input", fmt=fmt, source_comment=True)
        _put(ws, f"D{row}", metric.actual, kind="input", fmt=fmt, source_comment=True)
        _put(ws, f"E{row}", f"=(D{row}-B{row})/ABS(B{row})", kind="calc", fmt=FMT_PCT1)
        _put(ws, f"F{row}", f"=(D{row}-C{row})/ABS(C{row})", kind="calc", fmt=FMT_PCT1)
        _put(
            ws,
            f"G{row}",
            f'=IF(F{row}>{INLINE_TOLERANCE},"BEAT",IF(F{row}<-{INLINE_TOLERANCE},"MISS","IN-LINE"))',
            kind="calc",
            bold=True,
            fill=_classification_fill(metric.classification),
            align="center",
        )

    _section(ws, 18, "Research Snapshot", 7)
    snapshot = [
        (19, "Earnings Scorecard", result.earnings_scorecard),
        (20, "Strongest Surprise Metric", result.strongest_surprise_metric),
        (21, "Strongest Surprise", result.strongest_surprise),
    ]
    for row, label, value in snapshot:
        _put(ws, f"A{row}", label, kind="label", bold=True)
        if row == 21:
            _put(ws, f"B{row}", value, kind="python", fmt=FMT_PCT1)
        else:
            _put(ws, f"B{row}", value, kind="python", bold=True)

    ws.conditional_formatting.add(
        "F12:F15",
        FormulaRule(formula=["F12>0"], fill=PatternFill("solid", fgColor=_LIGHT_GREEN)),
    )
    ws.conditional_formatting.add(
        "F12:F15",
        FormulaRule(formula=["F12<0"], fill=PatternFill("solid", fgColor=_LIGHT_RED)),
    )


def _build_historical(ws: Worksheet) -> None:
    _title(ws, "Historical Performance", "Prior period versus reported actual performance.", 4)
    _widths(ws, {"A": 28, "B": 18, "C": 18, "D": 18})
    _section(ws, 4, "Operating Performance", 4)
    _header(ws, 5, ["Metric", "Prior Period", "Actual", "Change"])

    rows = [
        (6, "Revenue", "B12", "D12", FMT_NUM, FMT_PCT1),
        (7, "EBITDA", "B13", "D13", FMT_NUM, FMT_PCT1),
        (8, "EBITDA Margin", None, None, FMT_PCT1, FMT_BPS),
        (9, "EPS", "B14", "D14", FMT_EPS, FMT_PCT1),
        (10, "Free Cash Flow", "B15", "D15", FMT_NUM, FMT_PCT1),
        (11, "FCF / EBITDA", None, None, FMT_PCT1, FMT_PCT1),
    ]
    for row, label, prior_ref, actual_ref, value_fmt, change_fmt in rows:
        _put(ws, f"A{row}", label, kind="label", bold=True if row in {6,7,9,10} else False)
        if row == 8:
            _put(ws, "B8", f"={_cross(SHEET_SUMMARY, 'B13')}/{_cross(SHEET_SUMMARY, 'B12')}", kind="link", fmt=FMT_PCT1)
            _put(ws, "C8", f"={_cross(SHEET_SUMMARY, 'D13')}/{_cross(SHEET_SUMMARY, 'D12')}", kind="link", fmt=FMT_PCT1)
            _put(ws, "D8", "=(C8-B8)*10000", kind="calc", fmt=FMT_BPS)
        elif row == 11:
            _put(ws, "B11", f"={_cross(SHEET_SUMMARY, 'B15')}/{_cross(SHEET_SUMMARY, 'B13')}", kind="link", fmt=FMT_PCT1)
            _put(ws, "C11", f"={_cross(SHEET_SUMMARY, 'D15')}/{_cross(SHEET_SUMMARY, 'D13')}", kind="link", fmt=FMT_PCT1)
            _put(ws, "D11", "=C11-B11", kind="calc", fmt=FMT_PCT1)
        else:
            _put(ws, f"B{row}", f"={_cross(SHEET_SUMMARY, prior_ref)}", kind="link", fmt=value_fmt)
            _put(ws, f"C{row}", f"={_cross(SHEET_SUMMARY, actual_ref)}", kind="link", fmt=value_fmt)
            _put(ws, f"D{row}", f"=(C{row}-B{row})/ABS(B{row})", kind="calc", fmt=change_fmt)


def _build_consensus(ws: Worksheet) -> None:
    _title(ws, "Consensus vs Actual", "Expectation analysis and beat / miss classification.", 6)
    _widths(ws, {"A": 24, "B": 16, "C": 16, "D": 16, "E": 16, "F": 16})
    _section(ws, 4, "Expectation Bridge", 6)
    _header(ws, 5, ["Metric", "Consensus", "Actual", "Variance", "Surprise", "Result"])
    refs = [(6, "Revenue", 12, FMT_NUM), (7, "EBITDA", 13, FMT_NUM), (8, "EPS", 14, FMT_EPS), (9, "Free Cash Flow", 15, FMT_NUM)]
    for row, label, src_row, fmt in refs:
        _put(ws, f"A{row}", label, kind="label", bold=True)
        _put(ws, f"B{row}", f"={_cross(SHEET_SUMMARY, f'C{src_row}')}", kind="link", fmt=fmt)
        _put(ws, f"C{row}", f"={_cross(SHEET_SUMMARY, f'D{src_row}')}", kind="link", fmt=fmt)
        _put(ws, f"D{row}", f"=C{row}-B{row}", kind="calc", fmt=fmt)
        _put(ws, f"E{row}", f"=(C{row}-B{row})/ABS(B{row})", kind="calc", fmt=FMT_PCT1)
        _put(ws, f"F{row}", f"={_cross(SHEET_SUMMARY, f'G{src_row}')}", kind="link", bold=True, align="center")

    # Authentic earnings chart: currency metrics only; EPS is separately displayed in table.
    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = "Actual vs Consensus - Currency Metrics"
    chart.y_axis.title = "Currency (m)"
    chart.x_axis.title = "Metric"
    data = Reference(ws, min_col=2, max_col=3, min_row=5, max_row=9)
    cats = Reference(ws, min_col=1, min_row=6, max_row=9)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 7.5
    chart.width = 13
    chart.legend.position = "b"
    ws.add_chart(chart, "A12")


def _build_kpis(ws: Worksheet) -> None:
    _title(ws, "KPIs", "Growth, profitability and cash conversion metrics.", 4)
    _widths(ws, {"A": 32, "B": 18, "C": 18, "D": 22})

    _section(ws, 4, "Growth", 4)
    _header(ws, 5, ["KPI", "Value", "Reference", "Comment"])
    growth_rows = [(6, "Revenue YoY", "E12"), (7, "EBITDA YoY", "E13"), (8, "EPS YoY", "E14"), (9, "FCF YoY", "E15")]
    for row, label, ref in growth_rows:
        _put(ws, f"A{row}", label, kind="label")
        _put(ws, f"B{row}", f"={_cross(SHEET_SUMMARY, ref)}", kind="link", fmt=FMT_PCT1)
        _put(ws, f"C{row}", "Reported vs prior period", kind="label")

    _section(ws, 12, "Profitability & Cash Conversion", 4)
    kpis = [
        (13, "Prior EBITDA Margin", f"={_cross(SHEET_HISTORICAL, 'B8')}", FMT_PCT1),
        (14, "Consensus EBITDA Margin", f"={_cross(SHEET_SUMMARY, 'C13')}/{_cross(SHEET_SUMMARY, 'C12')}", FMT_PCT1),
        (15, "Actual EBITDA Margin", f"={_cross(SHEET_HISTORICAL, 'C8')}", FMT_PCT1),
        (16, "Margin vs Consensus", "=(B15-B14)*10000", FMT_BPS),
        (17, "YoY Margin Change", "=(B15-B13)*10000", FMT_BPS),
        (18, "FCF / EBITDA", f"={_cross(SHEET_SUMMARY, 'D15')}/{_cross(SHEET_SUMMARY, 'D13')}", FMT_PCT1),
    ]
    for row, label, formula, fmt in kpis:
        _put(ws, f"A{row}", label, kind="label", bold=row in {15,16,18})
        kind = "link" if "'" in formula and row not in {16,17} else "calc"
        _put(ws, f"B{row}", formula, kind=kind, fmt=fmt, bold=row in {15,16,18})


def _build_guidance(ws: Worksheet, result: EquityResearchResult) -> None:
    _title(ws, "Guidance", "Previous versus revised management guidance ranges.", 8)
    _widths(ws, {"A": 24, "B": 16, "C": 16, "D": 16, "E": 16, "F": 16, "G": 16, "H": 18})
    _section(ws, 4, "Management Guidance", 8)
    _header(ws, 5, ["Metric", "Prev Low", "Prev High", "Prev Mid", "New Low", "New High", "New Mid", "Revision"])

    rows = [
        (6, "Revenue Guidance", result.revenue_guidance, FMT_NUM),
        (7, "EBITDA Guidance", result.ebitda_guidance, FMT_NUM),
    ]
    raw_inputs = {
        6: (
            result.inputs.previous_revenue_guidance_low,
            result.inputs.previous_revenue_guidance_high,
            result.inputs.new_revenue_guidance_low,
            result.inputs.new_revenue_guidance_high,
        ),
        7: (
            result.inputs.previous_ebitda_guidance_low,
            result.inputs.previous_ebitda_guidance_high,
            result.inputs.new_ebitda_guidance_low,
            result.inputs.new_ebitda_guidance_high,
        ),
    }
    for row, label, guidance, fmt in rows:
        _put(ws, f"A{row}", label, kind="label", bold=True)
        p_low, p_high, n_low, n_high = raw_inputs[row]
        _put(ws, f"B{row}", p_low, kind="input", fmt=fmt, source_comment=True)
        _put(ws, f"C{row}", p_high, kind="input", fmt=fmt, source_comment=True)
        _put(ws, f"D{row}", f"=AVERAGE(B{row}:C{row})", kind="calc", fmt=fmt)
        _put(ws, f"E{row}", n_low, kind="input", fmt=fmt, source_comment=True)
        _put(ws, f"F{row}", n_high, kind="input", fmt=fmt, source_comment=True)
        _put(ws, f"G{row}", f"=AVERAGE(E{row}:F{row})", kind="calc", fmt=fmt)
        _put(ws, f"H{row}", f"=(G{row}-D{row})/D{row}", kind="calc", fmt=FMT_PCT1)

    _header(ws, 10, ["Metric", "Classification"])
    _put(ws, "A11", "Revenue Guidance", kind="label")
    _put(ws, "B11", '=IF(H6>0.005,"RAISED",IF(H6<-0.005,"LOWERED","UNCHANGED"))', kind="calc", bold=True, fill=_classification_fill(result.revenue_guidance.classification))
    _put(ws, "A12", "EBITDA Guidance", kind="label")
    _put(ws, "B12", '=IF(H7>0.005,"RAISED",IF(H7<-0.005,"LOWERED","UNCHANGED"))', kind="calc", bold=True, fill=_classification_fill(result.ebitda_guidance.classification))

    # Visual: midpoint comparison.
    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = "Guidance Midpoint Revision"
    chart.x_axis.title = "Currency (m)"
    chart.y_axis.title = "Metric"
    data = Reference(ws, min_col=4, max_col=7, min_row=5, max_row=7)
    cats = Reference(ws, min_col=1, min_row=6, max_row=7)
    # D:G contains midpoint + new low/high; restrict to D and G using custom data not trivial.
    # Use helper table instead for clean Previous Mid vs New Mid chart.
    _put(ws, "J5", "Metric", kind="label", bold=True)
    _put(ws, "K5", "Previous Mid", kind="label", bold=True)
    _put(ws, "L5", "New Mid", kind="label", bold=True)
    _put(ws, "J6", "Revenue", kind="label")
    _put(ws, "J7", "EBITDA", kind="label")
    _put(ws, "K6", "=D6", kind="calc", fmt=FMT_NUM)
    _put(ws, "L6", "=G6", kind="calc", fmt=FMT_NUM)
    _put(ws, "K7", "=D7", kind="calc", fmt=FMT_NUM)
    _put(ws, "L7", "=G7", kind="calc", fmt=FMT_NUM)
    chart_data = Reference(ws, min_col=11, max_col=12, min_row=5, max_row=7)
    chart_cats = Reference(ws, min_col=10, min_row=6, max_row=7)
    chart.add_data(chart_data, titles_from_data=True)
    chart.set_categories(chart_cats)
    chart.height = 6.5
    chart.width = 11
    chart.legend.position = "b"
    ws.add_chart(chart, "A15")
    ws.column_dimensions["J"].hidden = True
    ws.column_dimensions["K"].hidden = True
    ws.column_dimensions["L"].hidden = True


def _build_valuation(ws: Worksheet, result: EquityResearchResult) -> None:
    _title(ws, "Valuation", "Forward valuation snapshot using submitted market and estimate inputs.", 5)
    _widths(ws, {"A": 30, "B": 18, "C": 16, "D": 20, "E": 20})
    _section(ws, 4, "Market & Forward Inputs", 5)
    inputs = [
        (5, "Share Price", result.inputs.share_price, FMT_PRICE),
        (6, "Shares Outstanding (m)", result.inputs.shares_outstanding, FMT_NUM1),
        (7, "Net Debt (m)", result.inputs.net_debt, FMT_NUM),
        (8, "Forward Revenue (m)", result.inputs.forward_revenue, FMT_NUM),
        (9, "Forward EBITDA (m)", result.inputs.forward_ebitda, FMT_NUM),
        (10, "Forward EPS", result.inputs.forward_eps, FMT_EPS),
    ]
    for row, label, value, fmt in inputs:
        _put(ws, f"A{row}", label, kind="label", bold=True)
        _put(ws, f"B{row}", value, kind="input", fmt=fmt, source_comment=True)

    _section(ws, 13, "Valuation Snapshot", 5)
    vals = [
        (14, "Market Capitalisation (m)", "=B5*B6", FMT_NUM),
        (15, "Enterprise Value (m)", "=B14+B7", FMT_NUM),
        (16, "Forward P/E", "=B5/B10", FMT_MULTIPLE),
        (17, "EV / EBITDA", "=B15/B9", FMT_MULTIPLE),
        (18, "EV / Revenue", "=B15/B8", FMT_MULTIPLE),
        (19, "Net Debt / EBITDA", "=B7/B9", FMT_MULTIPLE),
    ]
    for row, label, formula, fmt in vals:
        _put(ws, f"A{row}", label, kind="label", bold=row in {14,15})
        _put(ws, f"B{row}", formula, kind="calc", fmt=fmt, bold=row in {14,15})

    # Valuation multiple chart.
    _put(ws, "D14", "Multiple", kind="label", bold=True)
    _put(ws, "E14", "Value", kind="label", bold=True)
    for r, (label, ref) in enumerate([("Forward P/E", "B16"), ("EV / EBITDA", "B17"), ("EV / Revenue", "B18"), ("Net Debt / EBITDA", "B19")], start=15):
        _put(ws, f"D{r}", label, kind="label")
        _put(ws, f"E{r}", f"={ref}", kind="calc", fmt=FMT_MULTIPLE)
    chart = BarChart()
    chart.type = "bar"
    chart.style = 10
    chart.title = "Forward Valuation Multiples"
    chart.x_axis.title = "Multiple (x)"
    data = Reference(ws, min_col=5, min_row=14, max_row=18)
    cats = Reference(ws, min_col=4, min_row=15, max_row=18)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 7
    chart.width = 11
    chart.legend = None
    ws.add_chart(chart, "D4")


def _build_takeaways(ws: Worksheet, result: EquityResearchResult) -> None:
    _title(ws, "Analyst Takeaways", "Deterministic observations generated from the Python ER engine.", 6)
    _widths(ws, {"A": 18, "B": 90, "C": 4, "D": 18, "E": 54, "F": 4})

    _section(ws, 4, "Key Takeaways", 6)
    for i, text in enumerate(result.takeaways, start=1):
        row = 4 + i
        _put(ws, f"A{row}", f"{i}.", kind="label", bold=True, align="center")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
        _put(ws, f"B{row}", text, kind="python", wrap=True)
        ws.row_dimensions[row].height = 36

    _section(ws, 9, "Catalysts", 6)
    for i, text in enumerate(result.catalysts, start=10):
        _put(ws, f"A{i}", "•", kind="label", bold=True, align="center")
        ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=6)
        _put(ws, f"B{i}", text, kind="python", wrap=True)
        ws.row_dimensions[i].height = 30

    risk_start = 11 + len(result.catalysts)
    _section(ws, risk_start, "Risks", 6)
    for i, text in enumerate(result.risks, start=risk_start + 1):
        _put(ws, f"A{i}", "•", kind="label", bold=True, align="center")
        ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=6)
        _put(ws, f"B{i}", text, kind="python", wrap=True)
        ws.row_dimensions[i].height = 30


def _build_checks(ws: Worksheet, result: EquityResearchResult) -> None:
    _title(ws, "Model Checks", "Python-engine reference values versus values calculated by Excel formulas.", 7)
    _widths(ws, {"A": 5, "B": 38, "C": 22, "D": 22, "E": 18, "F": 14, "G": 42})
    _put(ws, "A4", "Overall model status", kind="label", bold=True)
    _put(ws, "B4", '=IF(COUNTIF(F8:F19,"FAIL")=0,"ALL CHECKS PASS","CHECK MODEL")', kind="calc", bold=True, fill=_LIGHT_GREEN)
    _put(ws, "A5", "Absolute tolerance", kind="label", bold=True)
    _put(ws, "B5", CHECK_TOLERANCE, kind="input", fmt=FMT_CHECK, source_comment=True)

    _header(ws, 7, ["#", "Check", "Python / Reference", "Excel Value", "Difference", "Result", "Description"])

    checks = [
        (8, "Revenue surprise", result.revenue.surprise, f"={_cross(SHEET_SUMMARY, 'F12')}", "Revenue actual vs consensus"),
        (9, "EBITDA surprise", result.ebitda.surprise, f"={_cross(SHEET_SUMMARY, 'F13')}", "EBITDA actual vs consensus"),
        (10, "EPS surprise", result.eps.surprise, f"={_cross(SHEET_SUMMARY, 'F14')}", "EPS actual vs consensus"),
        (11, "FCF surprise", result.fcf.surprise, f"={_cross(SHEET_SUMMARY, 'F15')}", "Free cash flow actual vs consensus"),
        (12, "Actual EBITDA margin", result.actual_ebitda_margin, f"={_cross(SHEET_KPIS, 'B15')}", "Actual EBITDA / actual revenue"),
        (13, "Margin surprise (bps)", result.ebitda_margin_surprise_bps, f"={_cross(SHEET_KPIS, 'B16')}", "Actual margin less consensus margin"),
        (14, "Market capitalisation", result.market_cap, f"={_cross(SHEET_VALUATION, 'B14')}", "Share price x shares outstanding"),
        (15, "Enterprise value", result.enterprise_value, f"={_cross(SHEET_VALUATION, 'B15')}", "Market cap + net debt"),
        (16, "Forward P/E", result.forward_pe, f"={_cross(SHEET_VALUATION, 'B16')}", "Share price / forward EPS"),
        (17, "Forward EV / EBITDA", result.forward_ev_ebitda, f"={_cross(SHEET_VALUATION, 'B17')}", "Enterprise value / forward EBITDA"),
        (18, "Revenue guidance revision", result.revenue_guidance.midpoint_revision, f"={_cross(SHEET_GUIDANCE, 'H6')}", "New vs previous revenue midpoint"),
        (19, "EBITDA guidance revision", result.ebitda_guidance.midpoint_revision, f"={_cross(SHEET_GUIDANCE, 'H7')}", "New vs previous EBITDA midpoint"),
    ]
    pct_rows = {8,9,10,11,12,18,19}
    multiple_rows = {16,17}
    for idx, (row, label, py_value, formula, description) in enumerate(checks, start=1):
        fmt = FMT_CHECK
        if row in pct_rows:
            fmt = FMT_PCT2
        elif row == 13:
            fmt = FMT_BPS
        elif row in multiple_rows:
            fmt = FMT_MULTIPLE
        elif row in {14,15}:
            fmt = FMT_NUM
        _put(ws, f"A{row}", idx, kind="label")
        _put(ws, f"B{row}", label, kind="label")
        _put(ws, f"C{row}", py_value, kind="python", fmt=fmt)
        _put(ws, f"D{row}", formula, kind="link", fmt=fmt)
        _put(ws, f"E{row}", f"=D{row}-C{row}", kind="calc", fmt=FMT_CHECK)
        _put(ws, f"F{row}", f'=IF(ABS(E{row})<=$B$5,"PASS","FAIL")', kind="calc", bold=True, align="center")
        _put(ws, f"G{row}", description, kind="label", italic=True, wrap=True)

    ws.conditional_formatting.add(
        "F8:F19",
        FormulaRule(formula=['F8="PASS"'], fill=PatternFill("solid", fgColor=_LIGHT_GREEN)),
    )
    ws.conditional_formatting.add(
        "F8:F19",
        FormulaRule(formula=['F8="FAIL"'], fill=PatternFill("solid", fgColor=_LIGHT_RED)),
    )


def _build_sources(ws: Worksheet, result: EquityResearchResult, generated_at: datetime) -> None:
    _title(ws, "Data Sources & Methodology", "Controlled sample-data disclosure and model limitations.", 5)
    _widths(ws, {"A": 28, "B": 34, "C": 28, "D": 28, "E": 28})
    _section(ws, 4, "Source Register", 5)
    _header(ws, 5, ["Data / Output", "Source", "Period / Basis", "Status", "Notes"])
    rows = [
        (6, "Company identity", "Controlled sample dataset", result.inputs.period, "Illustrative", "Fictional issuer"),
        (7, "Prior results", "Controlled sample dataset", "Prior comparable period", "Illustrative", "Not company-reported live data"),
        (8, "Consensus estimates", "Controlled sample dataset", result.inputs.period, "Illustrative", "Not broker consensus"),
        (9, "Actual results", "Controlled sample dataset", result.inputs.period, "Illustrative", "Not live earnings data"),
        (10, "Guidance ranges", "Controlled sample dataset", "Previous vs current", "Illustrative", "Not management-issued live guidance"),
        (11, "Market inputs", "User / controlled sample", "Submitted assumptions", "Illustrative", "Share price is not a live quote"),
        (12, "Analyst takeaways", "Deterministic Python ER engine", "Calculated from supplied data", "Model output", "No LLM investment recommendation"),
    ]
    for row, *values in rows:
        for col, value in enumerate(values, start=1):
            _put(ws, f"{chr(64+col)}{row}", value, kind="label", wrap=True)

    _section(ws, 15, "Methodology & Limitations", 5)
    notes = [
        "Earnings surprises compare actual values with controlled consensus values using (Actual - Consensus) / |Consensus|.",
        "YoY growth compares actual values with the controlled prior-period values.",
        "Valuation multiples use the submitted share price, shares outstanding, net debt and forward estimates.",
        "This workbook is an illustrative automation demo. It is not investment advice, a rating, a price target or a live research product.",
        "Units are currency millions except per-share data, percentages, basis points and valuation multiples.",
    ]
    for i, note in enumerate(notes, start=16):
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=5)
        _put(ws, f"A{i}", note, kind="label", wrap=True)
        ws.row_dimensions[i].height = 28

    _put(ws, "A23", "Generated at", kind="label", bold=True)
    _put(ws, "B23", generated_at, kind="label")
    ws["B23"].number_format = "yyyy-mm-dd hh:mm:ss"


def _build_cover(ws: Worksheet, result: EquityResearchResult, generated_at: datetime) -> None:
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.merge_cells("A1:D2")
    ws["A1"] = "Equity Research | Post-Earnings Review"
    ws["A1"].font = Font(name=_FONT, size=20, bold=True, color=_WHITE)
    ws["A1"].fill = PatternFill("solid", fgColor=_DARK_NAVY)
    ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 14
    _widths(ws, {"A": 34, "B": 24, "C": 24, "D": 24})

    _put(ws, "A4", "Illustrative automated equity research model", kind="label", italic=True)
    cover_links = [
        (6, "Company", f"={_cross(SHEET_SUMMARY, 'B5')}", None),
        (7, "Ticker", f"={_cross(SHEET_SUMMARY, 'B6')}", None),
        (8, "Reporting Period", f"={_cross(SHEET_SUMMARY, 'B8')}", None),
        (9, "Earnings Scorecard", f"={_cross(SHEET_SUMMARY, 'B19')}", None),
        (11, "Revenue", f"={_cross(SHEET_SUMMARY, 'D12')}", FMT_NUM),
        (12, "Revenue Surprise", f"={_cross(SHEET_SUMMARY, 'F12')}", FMT_PCT1),
        (13, "EBITDA", f"={_cross(SHEET_SUMMARY, 'D13')}", FMT_NUM),
        (14, "EBITDA Surprise", f"={_cross(SHEET_SUMMARY, 'F13')}", FMT_PCT1),
        (15, "EPS", f"={_cross(SHEET_SUMMARY, 'D14')}", FMT_EPS),
        (16, "EPS Surprise", f"={_cross(SHEET_SUMMARY, 'F14')}", FMT_PCT1),
        (18, "Forward P/E", f"={_cross(SHEET_VALUATION, 'B16')}", FMT_MULTIPLE),
        (19, "EV / EBITDA", f"={_cross(SHEET_VALUATION, 'B17')}", FMT_MULTIPLE),
        (21, "Revenue Guidance", f"={_cross(SHEET_GUIDANCE, 'B11')}", None),
        (22, "EBITDA Guidance", f"={_cross(SHEET_GUIDANCE, 'B12')}", None),
        (24, "Model Checks", f"={_cross(SHEET_CHECKS, 'B4')}", None),
    ]
    for row, label, formula, fmt in cover_links:
        _put(ws, f"A{row}", label, kind="label", bold=True)
        _put(ws, f"B{row}", formula, kind="link", fmt=fmt, bold=row in {9,24})

    ws.merge_cells("A27:D27")
    _put(ws, "A27", "Controlled sample data | Fictional issuer | Not investment advice", kind="label", italic=True, wrap=True)
    ws.merge_cells("A29:D29")
    _put(ws, "A29", "See 09_Data_Sources for methodology, data-source status and limitations.", kind="label", italic=True, wrap=True)
    _put(ws, "A31", "Generated", kind="label", bold=True)
    _put(ws, "B31", generated_at, kind="label")
    ws["B31"].number_format = "yyyy-mm-dd hh:mm"


def build_equity_research_workbook(result: EquityResearchResult, generated_at: datetime | None = None) -> Workbook:
    generated_at = generated_at or datetime.now().replace(microsecond=0)
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    wb.calculation = CalcProperties(calcMode="auto", fullCalcOnLoad=True, forceFullCalc=True)

    for name in SHEET_NAMES:
        wb.create_sheet(name)

    _build_summary(wb[SHEET_SUMMARY], result)
    _build_historical(wb[SHEET_HISTORICAL])
    _build_consensus(wb[SHEET_CONSENSUS])
    _build_kpis(wb[SHEET_KPIS])
    _build_guidance(wb[SHEET_GUIDANCE], result)
    _build_valuation(wb[SHEET_VALUATION], result)
    _build_takeaways(wb[SHEET_TAKEAWAYS], result)
    _build_checks(wb[SHEET_CHECKS], result)
    _build_sources(wb[SHEET_SOURCES], result, generated_at)
    _build_cover(wb[SHEET_COVER], result, generated_at)

    wb.active = 0
    return wb


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text.strip())
    return cleaned.strip("_") or "period"


def _resolve_output_path(output: str | Path | None, ticker: str, period: str, generated_at: datetime) -> Path:
    if output is None:
        target = DEFAULT_OUTPUT_DIR
    else:
        target = Path(output).expanduser()

    if target.suffix:
        if target.suffix.lower() != ".xlsx":
            raise ValueError("Output path must use the .xlsx extension.")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    target.mkdir(parents=True, exist_ok=True)
    filename = f"{_slug(ticker).upper()}_ER_{_slug(period)}_{generated_at:%Y%m%d_%H%M%S}.xlsx"
    return target / filename


def generate_equity_research_workbook(
    result: EquityResearchResult,
    output: str | Path | None = None,
    generated_at: datetime | None = None,
) -> Path:
    """Generate, save and return a professional analyst-style ER workbook."""
    generated_at = generated_at or datetime.now().replace(microsecond=0)
    path = _resolve_output_path(output, result.inputs.ticker, result.inputs.period, generated_at)
    build_equity_research_workbook(result, generated_at).save(path)
    return path
