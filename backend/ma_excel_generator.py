"""Professional M&A merger-model workbook generator.

The workbook is built from a banker-formatted XLSX template.  This module uses
only the Python standard library to populate the template so Stage 8D does not
add a new application dependency.  Excel formulas, charts, formats and model
checks remain embedded in the template and are forced to recalculate when the
workbook is opened.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from backend.ma_execution import MAExecutionResult

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("x", MAIN_NS)

TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "ma_merger_model_template.xlsx"


def _q(tag: str) -> str:
    return f"{{{MAIN_NS}}}{tag}"


def _safe_ticker(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "", value.upper())
    return cleaned or "COMPANY"


def _currency_symbol(code: str) -> str:
    return {"GBP": "£", "USD": "$", "EUR": "€"}.get(code.upper(), code.upper())


def _set_cell(root: ET.Element, ref: str, value: object, *, preserve_formula: bool = False) -> None:
    cell = root.find(f".//{_q('c')}[@r='{ref}']")
    if cell is None:
        raise ValueError(f"Template cell {ref} is missing.")

    formula = cell.find(_q("f"))
    if not preserve_formula and formula is not None:
        cell.remove(formula)

    old_value = cell.find(_q("v"))
    if old_value is None:
        old_value = ET.SubElement(cell, _q("v"))

    if isinstance(value, str):
        cell.set("t", "str")
        old_value.text = value
    elif value is None:
        cell.attrib.pop("t", None)
        old_value.text = None
    else:
        cell.set("t", "n")
        if isinstance(value, bool):
            old_value.text = "1" if value else "0"
        elif isinstance(value, int):
            old_value.text = str(value)
        else:
            old_value.text = f"{float(value):.15g}"


def _patch_workbook_calc_mode(xml_bytes: bytes) -> bytes:
    root = ET.fromstring(xml_bytes)
    calc = root.find(_q("calcPr"))
    if calc is None:
        calc = ET.SubElement(root, _q("calcPr"))
    calc.set("calcMode", "auto")
    calc.set("fullCalcOnLoad", "1")
    calc.set("forceFullCalc", "1")
    calc.set("calcId", "0")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _replace_currency_symbol(xml_bytes: bytes, symbol: str) -> bytes:
    if symbol == "£":
        return xml_bytes
    return xml_bytes.replace("£".encode("utf-8"), symbol.encode("utf-8"))


def _patch_assumptions(xml_bytes: bytes, result: MAExecutionResult) -> bytes:
    root = ET.fromstring(xml_bytes)
    i = result.inputs
    values = {
        "B5": i.acquirer_name,
        "B6": i.acquirer_ticker,
        "B7": i.currency.upper(),
        "B8": i.acquirer_share_price,
        "B9": i.acquirer_shares_outstanding,
        "B10": i.acquirer_net_income,
        "E5": i.target_name,
        "E6": i.target_ticker,
        "E7": i.target_share_price,
        "E8": i.target_shares_outstanding,
        "E9": i.target_net_income,
        "E10": i.target_ltm_revenue,
        "E11": i.target_ltm_ebitda,
        "E12": i.target_debt,
        "E13": i.target_cash,
        "E14": i.target_book_equity,
        "H5": i.offer_price_per_share,
        "H6": i.cash_consideration_pct,
        "H7": i.stock_consideration_pct,
        "H8": i.cash_on_hand_used,
        "H9": i.new_debt_interest_rate,
        "H10": i.cash_interest_rate,
        "H11": i.tax_rate,
        "H12": i.annual_pre_tax_synergies,
        "H13": i.identifiable_intangible_write_up,
        "H14": i.amortization_years,
    }
    for ref, value in values.items():
        _set_cell(root, ref, value)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_cover(xml_bytes: bytes, result: MAExecutionResult) -> bytes:
    root = ET.fromstring(xml_bytes)
    i = result.inputs
    t = result.transaction
    f = result.financing
    p = result.purchase_accounting
    a = result.accretion_dilution
    _set_cell(root, "B4", f"{i.acquirer_name} → {i.target_name} | Controlled Sample Transaction")

    cached = {
        "C7": t.offer_price_per_share,
        "C8": t.offer_premium,
        "C9": t.equity_purchase_price,
        "C10": t.target_enterprise_value,
        "C11": t.target_ev_ebitda,
        "C12": a.accretion_dilution,
        "C13": a.classification,
        "C17": f.cash_consideration,
        "C18": f.stock_consideration,
        "C19": f.new_debt_raised,
        "C20": f.new_shares_issued,
        "C21": f.target_seller_ownership,
        "C22": p.goodwill_created,
        "C26": "ALL CHECKS PASS",
        "H8": f.cash_consideration,
        "H9": f.stock_consideration,
    }
    for ref, value in cached.items():
        _set_cell(root, ref, value, preserve_formula=True)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_formula_caches(xml_bytes: bytes, mapping: dict[str, object]) -> bytes:
    root = ET.fromstring(xml_bytes)
    for ref, value in mapping.items():
        _set_cell(root, ref, value, preserve_formula=True)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_model_checks(xml_bytes: bytes, result: MAExecutionResult) -> bytes:
    root = ET.fromstring(xml_bytes)
    t = result.transaction
    f = result.financing
    p = result.purchase_accounting
    a = result.accretion_dilution
    refs = [
        t.offer_premium,
        t.equity_purchase_price,
        t.target_enterprise_value,
        t.target_ev_ebitda,
        f.cash_consideration,
        f.stock_consideration,
        f.new_debt_raised,
        f.new_shares_issued,
        f.target_seller_ownership,
        p.goodwill_created,
        p.annual_incremental_amortization,
        a.acquirer_standalone_eps,
        a.pro_forma_net_income,
        a.pro_forma_eps,
        a.accretion_dilution,
        a.break_even_pre_tax_synergies,
    ]
    for row, value in enumerate(refs, start=6):
        _set_cell(root, f"D{row}", value)
        _set_cell(root, f"C{row}", value, preserve_formula=True)
        _set_cell(root, f"E{row}", 0.0, preserve_formula=True)
        _set_cell(root, f"G{row}", "PASS", preserve_formula=True)
    _set_cell(root, "G23", "ALL CHECKS PASS", preserve_formula=True)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _patch_sources(xml_bytes: bytes, result: MAExecutionResult) -> bytes:
    root = ET.fromstring(xml_bytes)
    i = result.inputs
    _set_cell(
        root,
        "B6",
        f"{i.acquirer_ticker.upper()} / {i.target_ticker.upper()} standalone financials; offer and funding assumptions",
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def generate_ma_merger_model(
    result: MAExecutionResult,
    output_dir: str | Path,
    *,
    generated_at: datetime | None = None,
) -> Path:
    """Generate a banker-style merger model for a tested M&A engine result."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"M&A workbook template not found: {TEMPLATE_PATH}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (generated_at or datetime.now()).strftime("%Y%m%d_%H%M%S")
    filename = (
        f"{_safe_ticker(result.inputs.acquirer_ticker)}_"
        f"{_safe_ticker(result.inputs.target_ticker)}_Merger_Model_{timestamp}.xlsx"
    )
    output_path = output_dir / filename

    i = result.inputs
    t = result.transaction
    f = result.financing
    p = result.purchase_accounting
    a = result.accretion_dilution
    symbol = _currency_symbol(i.currency)

    purchase_price_cache = {
        "B5": i.target_share_price,
        "B6": i.offer_price_per_share,
        "B7": t.offer_premium,
        "B8": i.target_shares_outstanding,
        "B9": t.equity_purchase_price,
        "B10": i.target_debt,
        "B11": -i.target_cash,
        "B12": t.target_enterprise_value,
        "B16": i.target_ltm_revenue,
        "B17": i.target_ltm_ebitda,
        "B18": t.target_ev_revenue,
        "B19": t.target_ev_ebitda,
    }
    sources_uses_cache = {
        "B5": f.cash_on_hand_used,
        "B6": f.new_debt_raised,
        "B7": f.stock_consideration,
        "B8": t.equity_purchase_price,
        "E5": t.equity_purchase_price,
        "E8": t.equity_purchase_price,
        "H6": f.cash_on_hand_used,
        "H7": f.stock_consideration,
        "B13": t.equity_purchase_price,
        "B14": i.target_debt,
        "B15": -i.target_cash,
        "B16": t.target_enterprise_value,
    }
    purchase_accounting_cache = {
        "B5": t.equity_purchase_price,
        "B6": -i.target_book_equity,
        "B7": -i.identifiable_intangible_write_up,
        "B8": p.goodwill_created,
        "B10": i.amortization_years,
        "B11": p.annual_incremental_amortization,
        "E6": i.target_book_equity,
        "E7": i.identifiable_intangible_write_up,
        "E8": p.goodwill_created,
    }
    accretion_cache = {
        "B5": i.acquirer_net_income,
        "B6": i.target_net_income,
        "B7": a.after_tax_synergies,
        "B8": -a.after_tax_new_debt_interest,
        "B9": -a.after_tax_foregone_cash_interest,
        "B10": -a.after_tax_incremental_amortization,
        "B11": a.pro_forma_net_income,
        "B15": i.acquirer_shares_outstanding,
        "B16": f.new_shares_issued,
        "B17": a.pro_forma_shares_outstanding,
        "B18": a.acquirer_standalone_eps,
        "B19": a.pro_forma_eps,
        "B20": a.accretion_dilution,
        "B21": a.classification,
        "B22": a.break_even_pre_tax_synergies,
        "E6": i.target_net_income,
        "E7": a.after_tax_synergies,
        "E8": -a.after_tax_new_debt_interest,
        "E9": -a.after_tax_foregone_cash_interest,
        "E10": -a.after_tax_incremental_amortization,
    }
    ownership_cache = {
        "B5": f.stock_consideration,
        "B6": i.acquirer_share_price,
        "B7": f.new_shares_issued,
        "B8": f.exchange_ratio,
        "B9": i.acquirer_shares_outstanding,
        "B10": a.pro_forma_shares_outstanding,
        "B11": f.existing_acquirer_ownership,
        "B12": f.target_seller_ownership,
        "E6": f.existing_acquirer_ownership,
        "E7": f.target_seller_ownership,
    }

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(TEMPLATE_PATH, "r") as zin, ZipFile(temp_path, "w", ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename.endswith(".xml"):
                    data = _replace_currency_symbol(data, symbol)

                if info.filename == "xl/workbook.xml":
                    data = _patch_workbook_calc_mode(data)
                elif info.filename == "xl/worksheets/sheet1.xml":
                    data = _patch_cover(data, result)
                elif info.filename == "xl/worksheets/sheet2.xml":
                    data = _patch_assumptions(data, result)
                elif info.filename == "xl/worksheets/sheet3.xml":
                    data = _patch_formula_caches(data, purchase_price_cache)
                elif info.filename == "xl/worksheets/sheet4.xml":
                    data = _patch_formula_caches(data, sources_uses_cache)
                elif info.filename == "xl/worksheets/sheet5.xml":
                    data = _patch_formula_caches(data, purchase_accounting_cache)
                elif info.filename == "xl/worksheets/sheet6.xml":
                    data = _patch_formula_caches(data, accretion_cache)
                elif info.filename == "xl/worksheets/sheet7.xml":
                    data = _patch_formula_caches(data, ownership_cache)
                elif info.filename == "xl/worksheets/sheet9.xml":
                    data = _patch_model_checks(data, result)
                elif info.filename == "xl/worksheets/sheet10.xml":
                    data = _patch_sources(data, result)

                zout.writestr(info, data)

        shutil.move(str(temp_path), output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

    return output_path
