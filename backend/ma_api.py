"""FastAPI router for the deterministic M&A / deal-execution engine.

Stage 8B intentionally keeps the API layer thin: the route validates request
shape, constructs ``MAExecutionInputs``, delegates all calculations to the
Stage 8A engine, and serializes the tested result. No transaction formulas are
duplicated here.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.ma_execution import MAExecutionInputs, run_ma_execution
from backend.ma_excel_generator import generate_ma_merger_model

router = APIRouter()
OUTPUTS_DIR = Path("outputs")


class MAExecutionRequest(BaseModel):
    acquirer_name: str = "Apex Systems plc"
    acquirer_ticker: str = "APX"
    target_name: str = "Meridian Analytics plc"
    target_ticker: str = "MDA"
    currency: str = "GBP"

    acquirer_share_price: float = 40.0
    acquirer_shares_outstanding: float = 250.0
    acquirer_net_income: float = 600.0

    target_share_price: float = 20.0
    target_shares_outstanding: float = 100.0
    target_net_income: float = 120.0
    target_ltm_revenue: float = 1500.0
    target_ltm_ebitda: float = 250.0
    target_debt: float = 500.0
    target_cash: float = 200.0
    target_book_equity: float = 900.0

    offer_price_per_share: float = 25.0
    cash_consideration_pct: float = 0.50
    stock_consideration_pct: float = 0.50
    cash_on_hand_used: float = 500.0
    new_debt_interest_rate: float = 0.055
    cash_interest_rate: float = 0.020
    tax_rate: float = 0.25
    annual_pre_tax_synergies: float = 100.0

    identifiable_intangible_write_up: float = 300.0
    amortization_years: int = 10


class TransactionResponse(BaseModel):
    offer_price_per_share: float
    offer_premium: float
    equity_purchase_price: float
    target_enterprise_value: float
    target_ev_revenue: float
    target_ev_ebitda: float


class FinancingResponse(BaseModel):
    cash_consideration: float
    stock_consideration: float
    cash_on_hand_used: float
    new_debt_raised: float
    new_shares_issued: float
    exchange_ratio: float
    existing_acquirer_ownership: float
    target_seller_ownership: float


class PurchaseAccountingResponse(BaseModel):
    target_book_equity: float
    identifiable_intangible_write_up: float
    goodwill_created: float
    annual_incremental_amortization: float


class AccretionDilutionResponse(BaseModel):
    acquirer_standalone_eps: float
    pro_forma_net_income: float
    pro_forma_shares_outstanding: float
    pro_forma_eps: float
    accretion_dilution: float
    classification: str
    after_tax_synergies: float
    after_tax_new_debt_interest: float
    after_tax_foregone_cash_interest: float
    after_tax_incremental_amortization: float
    break_even_pre_tax_synergies: float


class MAExecutionResponse(BaseModel):
    acquirer_name: str
    acquirer_ticker: str
    target_name: str
    target_ticker: str
    currency: str
    transaction: TransactionResponse
    financing: FinancingResponse
    purchase_accounting: PurchaseAccountingResponse
    accretion_dilution: AccretionDilutionResponse
    key_takeaways: list[str]
    execution_risks: list[str]


def build_ma_execution_response(request: MAExecutionRequest) -> MAExecutionResponse:
    """Run the Stage 8A engine and serialize its result for the API."""
    try:
        inputs = MAExecutionInputs(**request.model_dump())
        result = run_ma_execution(inputs)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body"], "msg": str(exc), "type": "value_error"}],
        ) from exc

    return MAExecutionResponse.model_validate(result.to_dict())


@router.post("/api/ma-execution", response_model=MAExecutionResponse)
def calculate_ma_execution(request: MAExecutionRequest) -> MAExecutionResponse:
    """Return deterministic M&A transaction and accretion/dilution analytics."""
    return build_ma_execution_response(request)

@router.post("/api/ma-execution/excel")
def download_ma_execution_excel(request: MAExecutionRequest) -> FileResponse:
    """Generate and download the professional M&A merger model workbook."""
    try:
        inputs = MAExecutionInputs(**request.model_dump())
        result = run_ma_execution(inputs)
        path = generate_ma_merger_model(result, OUTPUTS_DIR)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body"], "msg": str(exc), "type": "value_error"}],
        ) from exc
    except (OSError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the merger model workbook.",
        ) from exc

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )

