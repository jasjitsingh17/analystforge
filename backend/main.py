from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.ma_api import router as ma_router
from backend.dcf import DCFInputs, DCFResult, run_dcf
from backend.excel_generator import generate_dcf_workbook
from backend.equity_research import (
    EquityResearchInputs,
    EquityResearchResult,
    run_equity_research,
)
from backend.equity_research_excel import generate_equity_research_workbook
from backend.equity_research_report import generate_equity_research_report_html


APP_NAME = "Financial Analyst Automation Platform"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

app = FastAPI(title=APP_NAME)
app.include_router(ma_router)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# Request model (API-layer validation)
# ---------------------------------------------------------------------------


class DCFRequest(BaseModel):
    """JSON body accepted by POST /api/dcf.

    Pydantic checks types and ranges before any financial code runs.
    Rates are decimals (0.085 = 8.5%).
    """

    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    company_name: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    share_price: float = Field(gt=0)
    forecast_years: int = Field(gt=0, strict=True)
    revenue_growth: float
    ebitda_margin: float
    tax_rate: float = Field(ge=0, le=1)
    wacc: float = Field(gt=0)
    terminal_growth: float = Field(ge=0)
    net_debt: float
    shares_outstanding: float = Field(gt=0)

    @model_validator(mode="after")
    def wacc_must_exceed_terminal_growth(self) -> "DCFRequest":
        if self.wacc <= self.terminal_growth:
            raise ValueError("WACC must be greater than terminal growth.")
        return self


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ForecastYear(BaseModel):
    """One forecast year; fields mirror the engine's YearProjection."""

    year: int
    revenue: float
    ebitda: float
    depreciation_amortization: float
    ebit: float
    taxes: float
    nopat: float
    capex: float
    change_in_nwc: float
    ufcf: float
    discount_factor: float
    pv_ufcf: float


class DCFResponse(BaseModel):
    """JSON returned by POST /api/dcf, built from the engine's DCFResult."""

    company_name: str
    ticker: str
    current_share_price: float
    forecast_years: int
    forecast: list[ForecastYear]
    sum_pv_ufcf: float
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    shares_outstanding: float
    implied_share_price: float
    upside_downside: float


class SensitivityResponse(BaseModel):
    """5x5 implied-share-price sensitivity table around the submitted base case."""

    wacc_values: list[float]
    terminal_growth_values: list[float]
    implied_share_prices: list[list[float | None]]
    base_row: int
    base_column: int
    base_implied_share_price: float



class EquityMetricResponse(BaseModel):
    prior: float
    consensus: float
    actual: float
    yoy_growth: float
    surprise: float
    classification: str


class EquityGuidanceResponse(BaseModel):
    previous_low: float
    previous_high: float
    previous_midpoint: float
    new_low: float
    new_high: float
    new_midpoint: float
    midpoint_revision: float
    classification: str


class EquityResearchRequest(BaseModel):
    """Inputs accepted by POST /api/equity-research.

    Stage 6B intentionally accepts explicit earnings, consensus, guidance and
    valuation inputs. The deterministic equity-research engine remains the
    single source of truth for calculations and analyst commentary.
    """

    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False)

    company_name: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    period: str = Field(min_length=1)
    share_price: float
    shares_outstanding: float
    net_debt: float

    prior_revenue: float
    consensus_revenue: float
    actual_revenue: float
    prior_ebitda: float
    consensus_ebitda: float
    actual_ebitda: float
    prior_eps: float
    consensus_eps: float
    actual_eps: float
    prior_fcf: float
    consensus_fcf: float
    actual_fcf: float

    forward_revenue: float
    forward_ebitda: float
    forward_eps: float

    previous_revenue_guidance_low: float
    previous_revenue_guidance_high: float
    new_revenue_guidance_low: float
    new_revenue_guidance_high: float
    previous_ebitda_guidance_low: float
    previous_ebitda_guidance_high: float
    new_ebitda_guidance_low: float
    new_ebitda_guidance_high: float


class EquityResearchResponse(BaseModel):
    company_name: str
    ticker: str
    currency: str
    period: str
    share_price: float
    shares_outstanding: float
    net_debt: float

    revenue: EquityMetricResponse
    ebitda: EquityMetricResponse
    eps: EquityMetricResponse
    fcf: EquityMetricResponse

    prior_ebitda_margin: float
    consensus_ebitda_margin: float
    actual_ebitda_margin: float
    ebitda_margin_surprise: float
    ebitda_margin_surprise_bps: float
    ebitda_margin_yoy_change_bps: float
    fcf_conversion: float

    market_cap: float
    enterprise_value: float
    forward_pe: float
    forward_ev_ebitda: float
    forward_ev_revenue: float
    net_debt_ebitda: float

    revenue_guidance: EquityGuidanceResponse
    ebitda_guidance: EquityGuidanceResponse

    strongest_surprise_metric: str
    strongest_surprise: float
    earnings_scorecard: str
    takeaways: list[str]
    catalysts: list[str]
    risks: list[str]





def build_equity_research_response(result: EquityResearchResult) -> EquityResearchResponse:
    """Copy the tested engine's structured result into the API model."""
    return EquityResearchResponse.model_validate(result.to_dict())


def run_equity_research_engine(request: EquityResearchRequest) -> EquityResearchResult:
    """Run the ER engine and normalize its validation errors to HTTP 422."""
    try:
        inputs = EquityResearchInputs(**request.model_dump())
        return run_equity_research(inputs)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body"], "msg": str(exc), "type": "value_error"}],
        ) from exc

def build_response(result: DCFResult) -> DCFResponse:
    """Copy engine results into the response model. No calculations here."""
    return DCFResponse(
        company_name=result.inputs.company_name,
        ticker=result.inputs.ticker,
        current_share_price=result.current_share_price,
        forecast_years=result.inputs.forecast_years,
        forecast=[ForecastYear(**asdict(year)) for year in result.projections],
        sum_pv_ufcf=result.sum_pv_ufcf,
        terminal_value=result.terminal_value,
        pv_terminal_value=result.pv_terminal_value,
        enterprise_value=result.enterprise_value,
        net_debt=result.net_debt,
        equity_value=result.equity_value,
        shares_outstanding=result.shares_outstanding,
        implied_share_price=result.implied_share_price,
        upside_downside=result.upside_downside,
    )


def run_engine(request: DCFRequest) -> DCFResult:
    """Run the tested Python DCF engine and normalize engine validation errors."""
    try:
        return run_dcf(DCFInputs(**request.model_dump()))
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body"], "msg": str(exc), "type": "value_error"}],
        ) from exc


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def read_root() -> FileResponse:
    """Serve the browser frontend."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}





@app.post("/api/equity-research", response_model=EquityResearchResponse)
def calculate_equity_research(request: EquityResearchRequest) -> EquityResearchResponse:
    """Run deterministic post-earnings equity-research analysis."""
    return build_equity_research_response(run_equity_research_engine(request))


@app.post("/api/equity-research/report", response_class=HTMLResponse)
def open_equity_research_report(request: EquityResearchRequest) -> HTMLResponse:
    """Return a self-contained, print-ready Equity Research note."""
    result = run_equity_research_engine(request)
    html = generate_equity_research_report_html(result)
    return HTMLResponse(content=html, status_code=200)


@app.post("/api/equity-research/excel")
def download_equity_research_excel(request: EquityResearchRequest) -> FileResponse:
    """Generate and download the analyst-style Equity Research workbook.

    The workbook is built from the same tested ``EquityResearchResult`` used by
    the browser dashboard, so the API layer does not duplicate research logic.
    """
    result = run_equity_research_engine(request)
    try:
        path = generate_equity_research_workbook(result, OUTPUTS_DIR)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the Equity Research workbook.",
        ) from exc

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@app.post("/api/dcf", response_model=DCFResponse)
def calculate_dcf(request: DCFRequest) -> DCFResponse:
    """Run the DCF engine on validated input and return its results."""
    return build_response(run_engine(request))


@app.post("/api/dcf/excel")
def download_dcf_excel(request: DCFRequest) -> FileResponse:
    """Generate and download the professional Excel DCF model.

    The workbook is built from the same tested ``DCFResult`` used by the browser
    valuation. Financial logic is not duplicated in the API layer.
    """
    result = run_engine(request)
    try:
        path = generate_dcf_workbook(result, OUTPUTS_DIR)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the Excel model.",
        ) from exc

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@app.post("/api/dcf/sensitivity", response_model=SensitivityResponse)
def calculate_dcf_sensitivity(request: DCFRequest) -> SensitivityResponse:
    """Return a 5x5 WACC / terminal-growth sensitivity matrix.

    Every populated cell is calculated by the same tested Python DCF engine used
    by POST /api/dcf. No valuation formula is duplicated in the API layer.
    """
    base_result = run_engine(request)
    base = request.model_dump()

    wacc_offsets = (-0.010, -0.005, 0.0, 0.005, 0.010)
    growth_offsets = (-0.010, -0.005, 0.0, 0.005, 0.010)
    wacc_values = [round(request.wacc + offset, 10) for offset in wacc_offsets]
    growth_values = [round(request.terminal_growth + offset, 10) for offset in growth_offsets]

    matrix: list[list[float | None]] = []
    for growth in growth_values:
        row: list[float | None] = []
        for wacc in wacc_values:
            if wacc <= 0 or growth < 0 or wacc <= growth:
                row.append(None)
                continue

            try:
                inputs = DCFInputs(**{**base, "wacc": wacc, "terminal_growth": growth})
                row.append(run_dcf(inputs).implied_share_price)
            except ValueError:
                row.append(None)
        matrix.append(row)

    return SensitivityResponse(
        wacc_values=wacc_values,
        terminal_growth_values=growth_values,
        implied_share_prices=matrix,
        base_row=2,
        base_column=2,
        base_implied_share_price=base_result.implied_share_price,
    )
