from __future__ import annotations

from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pytest

from backend.ma_execution import MAExecutionInputs, run_ma_execution
from backend.ma_excel_generator import TEMPLATE_PATH, generate_ma_merger_model

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _generate(tmp_path: Path, inputs: MAExecutionInputs | None = None) -> Path:
    result = run_ma_execution(inputs or MAExecutionInputs())
    return generate_ma_merger_model(
        result,
        tmp_path,
        generated_at=datetime(2026, 9, 25, 23, 55, 0),
    )


def _read(path: Path, name: str) -> bytes:
    with ZipFile(path) as zf:
        return zf.read(name)


def _sheet_names(path: Path) -> list[str]:
    root = ET.fromstring(_read(path, "xl/workbook.xml"))
    return [node.attrib["name"] for node in root.findall(f".//{{{MAIN_NS}}}sheet")]


def _cell_value(path: Path, sheet_number: int, ref: str) -> str | None:
    root = ET.fromstring(_read(path, f"xl/worksheets/sheet{sheet_number}.xml"))
    cell = root.find(f".//{{{MAIN_NS}}}c[@r='{ref}']")
    assert cell is not None, ref
    node = cell.find(f"{{{MAIN_NS}}}v")
    return None if node is None else node.text


def test_template_exists():
    assert TEMPLATE_PATH.exists()


def test_generator_creates_xlsx(tmp_path):
    path = _generate(tmp_path)
    assert path.exists()
    assert path.suffix == ".xlsx"


def test_generator_filename_is_deterministic(tmp_path):
    path = _generate(tmp_path)
    assert path.name == "APX_MDA_Merger_Model_20260925_235500.xlsx"


def test_generated_file_is_valid_zip(tmp_path):
    path = _generate(tmp_path)
    with ZipFile(path) as zf:
        assert "xl/workbook.xml" in zf.namelist()


def test_workbook_has_exactly_ten_sheets(tmp_path):
    assert len(_sheet_names(_generate(tmp_path))) == 10


def test_workbook_sheet_order_is_professional(tmp_path):
    assert _sheet_names(_generate(tmp_path)) == [
        "00_Cover",
        "01_Transaction_Assumptions",
        "02_Purchase_Price",
        "03_Sources_Uses",
        "04_Purchase_Accounting",
        "05_Accretion_Dilution",
        "06_Pro_Forma_Ownership",
        "07_Sensitivity",
        "08_Model_Checks",
        "09_Data_Sources",
    ]


def test_workbook_forces_excel_recalculation(tmp_path):
    xml = _read(_generate(tmp_path), "xl/workbook.xml").decode()
    assert 'calcMode="auto"' in xml
    assert 'fullCalcOnLoad="1"' in xml
    assert 'forceFullCalc="1"' in xml


@pytest.mark.parametrize(
    "sheet_number,formula_text",
    [
        (3, "B6-B5"),
        (4, "SUM(B5:B7)"),
        (5, "SUM(B5:B7)"),
        (6, "SUM(B5:B10)"),
        (7, "SUM(B7,B9)"),
        (8, "ABS"),
        (9, "ABS"),
    ],
)
def test_core_sheets_contain_excel_formulas(tmp_path, sheet_number, formula_text):
    root = ET.fromstring(_read(_generate(tmp_path), f"xl/worksheets/sheet{sheet_number}.xml"))
    formulas = [node.text or "" for node in root.findall(f".//{{{MAIN_NS}}}f")]
    assert formulas, f"No Excel formulas found on sheet {sheet_number}"
    assert any(formula_text in formula for formula in formulas), (
        f"Expected formula fragment {formula_text!r} on sheet {sheet_number}; "
        f"found {formulas}"
    )


def test_finance_styles_include_blue_hardcodes(tmp_path):
    styles = _read(_generate(tmp_path), "xl/styles.xml").decode()
    assert "FF0000FF" in styles


def test_finance_styles_include_green_cross_sheet_links(tmp_path):
    styles = _read(_generate(tmp_path), "xl/styles.xml").decode()
    assert "FF008000" in styles


def test_finance_styles_include_purple_python_references(tmp_path):
    styles = _read(_generate(tmp_path), "xl/styles.xml").decode()
    assert "FF7030A0" in styles


def test_finance_styles_include_red_negatives(tmp_path):
    styles = _read(_generate(tmp_path), "xl/styles.xml").decode()
    assert "FFC00000" in styles
    assert "[Red]" in styles


def test_finance_formats_display_zero_as_dash(tmp_path):
    styles = _read(_generate(tmp_path), "xl/styles.xml").decode()
    assert ";-" in styles


def test_workbook_contains_five_professional_charts(tmp_path):
    with ZipFile(_generate(tmp_path)) as zf:
        charts = [n for n in zf.namelist() if n.startswith("xl/drawings/charts/chart") and n.endswith(".xml")]
    assert len(charts) == 5


@pytest.mark.parametrize(
    "ref,expected",
    [
        ("B5", "Apex Systems plc"),
        ("B6", "APX"),
        ("B7", "GBP"),
        ("B8", "40"),
        ("B9", "250"),
        ("B10", "600"),
        ("E5", "Meridian Analytics plc"),
        ("E6", "MDA"),
        ("E7", "20"),
        ("E8", "100"),
        ("E9", "120"),
        ("E10", "1500"),
        ("E11", "250"),
        ("E12", "500"),
        ("E13", "200"),
        ("E14", "900"),
        ("H5", "25"),
        ("H6", "0.5"),
        ("H7", "0.5"),
        ("H8", "500"),
        ("H9", "0.055"),
        ("H10", "0.02"),
        ("H11", "0.25"),
        ("H12", "100"),
        ("H13", "300"),
        ("H14", "10"),
    ],
)
def test_default_assumptions_are_written_to_input_sheet(tmp_path, ref, expected):
    assert _cell_value(_generate(tmp_path), 2, ref) == expected


@pytest.mark.parametrize(
    "row,expected",
    [
        (6, 0.25),
        (7, 2500.0),
        (8, 2800.0),
        (9, 11.2),
        (10, 1250.0),
        (11, 1250.0),
        (12, 750.0),
        (13, 31.25),
        (14, 1 / 9),
        (15, 1300.0),
        (16, 30.0),
        (17, 2.4),
        (18, 734.0625),
        (19, 2.61),
        (20, 0.0875),
        (21, 21.25),
    ],
)
def test_model_checks_embed_python_reference_values(tmp_path, row, expected):
    actual = float(_cell_value(_generate(tmp_path), 9, f"D{row}"))
    assert actual == pytest.approx(expected)


def test_model_checks_show_all_checks_pass_cached(tmp_path):
    assert _cell_value(_generate(tmp_path), 9, "G23") == "ALL CHECKS PASS"


def test_cover_uses_current_company_names(tmp_path):
    value = _cell_value(_generate(tmp_path), 1, "B4")
    assert "Apex Systems plc" in value
    assert "Meridian Analytics plc" in value


def test_data_sources_use_current_tickers(tmp_path):
    assert _cell_value(_generate(tmp_path), 10, "B6").startswith("APX / MDA")


def test_custom_company_names_flow_into_workbook(tmp_path):
    inputs = MAExecutionInputs(acquirer_name="Northstar plc", target_name="Vertex plc")
    path = _generate(tmp_path, inputs)
    assert "Northstar plc" in (_cell_value(path, 1, "B4") or "")
    assert "Vertex plc" in (_cell_value(path, 1, "B4") or "")


def test_custom_tickers_flow_into_filename(tmp_path):
    inputs = MAExecutionInputs(acquirer_ticker="NST", target_ticker="VTX")
    path = _generate(tmp_path, inputs)
    assert path.name.startswith("NST_VTX_Merger_Model_")


def test_custom_offer_price_is_written(tmp_path):
    inputs = MAExecutionInputs(offer_price_per_share=24.0)
    assert _cell_value(_generate(tmp_path, inputs), 2, "H5") == "24"


def test_custom_funding_mix_is_written(tmp_path):
    inputs = MAExecutionInputs(cash_consideration_pct=0.6, stock_consideration_pct=0.4, cash_on_hand_used=500)
    path = _generate(tmp_path, inputs)
    assert _cell_value(path, 2, "H6") == "0.6"
    assert _cell_value(path, 2, "H7") == "0.4"


def test_custom_synergies_are_written(tmp_path):
    inputs = MAExecutionInputs(annual_pre_tax_synergies=125.0)
    assert _cell_value(_generate(tmp_path, inputs), 2, "H12") == "125"


def test_usd_currency_replaces_pound_symbol(tmp_path):
    path = _generate(tmp_path, MAExecutionInputs(currency="USD"))
    all_xml = b"".join(_read(path, name) for name in ZipFile(path).namelist() if name.endswith(".xml"))
    assert b"\xc2\xa3" not in all_xml
    assert b"$m" in all_xml


def test_generator_creates_missing_output_directory(tmp_path):
    target = tmp_path / "nested" / "models"
    path = _generate(target)
    assert target.exists()
    assert path.parent == target


def test_no_literal_excel_error_tokens_in_generated_xml(tmp_path):
    path = _generate(tmp_path)
    with ZipFile(path) as zf:
        xml = "\n".join(zf.read(n).decode("utf-8", errors="ignore") for n in zf.namelist() if n.endswith(".xml"))
    for token in ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"):
        assert token not in xml


def test_workbook_does_not_reintroduce_sales_and_trading(tmp_path):
    path = _generate(tmp_path)
    with ZipFile(path) as zf:
        xml = "\n".join(zf.read(n).decode("utf-8", errors="ignore") for n in zf.namelist() if n.endswith(".xml"))
    assert "Sales & Trading" not in xml
    assert "market-monitor" not in xml
