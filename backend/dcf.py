"""Discounted Cash Flow (DCF) calculation engine.

This module is the single source of truth for every DCF number in the
platform. The future API and the future Excel generator must read their
figures from the structured ``DCFResult`` returned by ``run_dcf`` rather than
re-calculating anything.

Design
------
* Each formula lives in its own small, pure function so it can be audited
  and unit-tested in isolation.
* ``run_dcf`` only orchestrates those functions; it contains no formulas.
* Inputs and outputs are immutable dataclasses.

Simplifications (v1)
--------------------
* Historical data is CONTROLLED SAMPLE DATA (see ``CONTROLLED_SAMPLE_HISTORICALS``).
  It is not live or company-reported data.
* D&A, CapEx and Change in NWC are held flat at their latest historical value.
* Cash flows are discounted with an end-of-year convention (no mid-year).
* Taxes = EBIT * tax rate, even if EBIT were negative (no loss carry-forwards).
* Terminal value uses the Gordon Growth (perpetuity growth) method only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Historical data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HistoricalData:
    """Historical financials, oldest year first, all in the same currency unit."""

    revenue: tuple[float, ...]
    ebitda: tuple[float, ...]
    depreciation_amortization: tuple[float, ...]
    capex: tuple[float, ...]
    change_in_nwc: tuple[float, ...]

    def __post_init__(self) -> None:
        lengths = {
            len(self.revenue),
            len(self.ebitda),
            len(self.depreciation_amortization),
            len(self.capex),
            len(self.change_in_nwc),
        }
        if len(lengths) != 1:
            raise ValueError("All historical series must have the same length.")
        if 0 in lengths:
            raise ValueError("Historical series must not be empty.")

    @property
    def latest_revenue(self) -> float:
        return self.revenue[-1]

    @property
    def latest_depreciation_amortization(self) -> float:
        return self.depreciation_amortization[-1]

    @property
    def latest_capex(self) -> float:
        return self.capex[-1]

    @property
    def latest_change_in_nwc(self) -> float:
        return self.change_in_nwc[-1]


# CONTROLLED SAMPLE DATA - a simplification for version 1.
# These figures are illustrative, not taken from any real company filing.
CONTROLLED_SAMPLE_HISTORICALS = HistoricalData(
    revenue=(100_000.0, 110_000.0, 120_000.0),
    ebitda=(25_000.0, 28_000.0, 31_000.0),
    depreciation_amortization=(5_000.0, 5_500.0, 6_000.0),
    capex=(6_000.0, 6_500.0, 7_000.0),
    change_in_nwc=(2_000.0, 2_200.0, 2_400.0),
)


# ---------------------------------------------------------------------------
# DCF inputs (validated on construction)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DCFInputs:
    """User-supplied valuation assumptions.

    Rates are decimals (0.085 = 8.5%). Money amounts share one currency unit.
    Invalid combinations raise ``ValueError`` at construction, so a
    ``DCFInputs`` object that exists is always valid.
    """

    company_name: str
    ticker: str
    share_price: float
    forecast_years: int
    revenue_growth: float
    ebitda_margin: float
    tax_rate: float
    wacc: float
    terminal_growth: float
    net_debt: float
    shares_outstanding: float

    def __post_init__(self) -> None:
        if self.share_price <= 0:
            raise ValueError("Share price must be greater than zero.")
        if self.shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be greater than zero.")
        if (
            isinstance(self.forecast_years, bool)
            or not isinstance(self.forecast_years, int)
            or self.forecast_years <= 0
        ):
            raise ValueError("Forecast years must be a whole number greater than zero.")
        if not 0 <= self.tax_rate <= 1:
            raise ValueError("Tax rate must be between 0 and 1.")
        if self.wacc <= 0:
            raise ValueError("WACC must be greater than zero.")
        if self.terminal_growth < 0:
            raise ValueError("Terminal growth must not be negative.")
        # Checked last so the more specific WACC / growth messages win first.
        if self.wacc <= self.terminal_growth:
            raise ValueError("WACC must be greater than terminal growth.")


# ---------------------------------------------------------------------------
# Output structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class YearProjection:
    """All line items for one forecast year (year 1 = first forecast year)."""

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


@dataclass(frozen=True)
class DCFResult:
    """Complete DCF output. The Excel generator should consume ``to_dict()``."""

    inputs: DCFInputs
    historical: HistoricalData
    projections: tuple[YearProjection, ...]
    sum_pv_ufcf: float
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    shares_outstanding: float
    implied_share_price: float
    current_share_price: float
    upside_downside: float

    def _column(self, name: str) -> list[float]:
        return [getattr(p, name) for p in self.projections]

    @property
    def forecast_years(self) -> list[int]:
        return [p.year for p in self.projections]

    @property
    def revenue(self) -> list[float]:
        return self._column("revenue")

    @property
    def ebitda(self) -> list[float]:
        return self._column("ebitda")

    @property
    def depreciation_amortization(self) -> list[float]:
        return self._column("depreciation_amortization")

    @property
    def ebit(self) -> list[float]:
        return self._column("ebit")

    @property
    def taxes(self) -> list[float]:
        return self._column("taxes")

    @property
    def nopat(self) -> list[float]:
        return self._column("nopat")

    @property
    def capex(self) -> list[float]:
        return self._column("capex")

    @property
    def change_in_nwc(self) -> list[float]:
        return self._column("change_in_nwc")

    @property
    def ufcf(self) -> list[float]:
        return self._column("ufcf")

    @property
    def discount_factor(self) -> list[float]:
        return self._column("discount_factor")

    @property
    def pv_ufcf(self) -> list[float]:
        return self._column("pv_ufcf")

    def to_dict(self) -> dict[str, Any]:
        """Flat, column-oriented dictionary for the API and Excel generator.

        Per-year items are lists (one value per forecast year); valuation
        outputs are scalars. Every value is the exact Python result, so any
        consumer shows the same numbers as the tests.
        """
        return {
            "company_name": self.inputs.company_name,
            "ticker": self.inputs.ticker,
            "forecast_years": self.forecast_years,
            "revenue": self.revenue,
            "ebitda": self.ebitda,
            "depreciation_amortization": self.depreciation_amortization,
            "ebit": self.ebit,
            "taxes": self.taxes,
            "nopat": self.nopat,
            "capex": self.capex,
            "change_in_nwc": self.change_in_nwc,
            "ufcf": self.ufcf,
            "discount_factor": self.discount_factor,
            "pv_ufcf": self.pv_ufcf,
            "sum_pv_ufcf": self.sum_pv_ufcf,
            "terminal_value": self.terminal_value,
            "pv_terminal_value": self.pv_terminal_value,
            "enterprise_value": self.enterprise_value,
            "net_debt": self.net_debt,
            "equity_value": self.equity_value,
            "shares_outstanding": self.shares_outstanding,
            "implied_share_price": self.implied_share_price,
            "current_share_price": self.current_share_price,
            "upside_downside": self.upside_downside,
        }


# ---------------------------------------------------------------------------
# Building-block formulas (pure functions)
# ---------------------------------------------------------------------------


def forecast_revenue(latest_revenue: float, growth: float, years: int) -> list[float]:
    """Project revenue forward at a constant growth rate.

    Formula:  Revenue_t = Revenue_(t-1) * (1 + Revenue Growth)
    Meaning:  Each year's sales are last year's sales grown by a fixed rate.
    Inputs:   latest_revenue (last historical year), growth (decimal), years.
    Output:   List of revenues for forecast years 1..years.
    """
    revenues: list[float] = []
    previous = latest_revenue
    for _ in range(years):
        previous = previous * (1 + growth)
        revenues.append(previous)
    return revenues


def calculate_ebitda(revenue: float, ebitda_margin: float) -> float:
    """EBITDA = Revenue * EBITDA Margin.

    Meaning: Operating profit before depreciation, amortisation, interest, tax.
    Inputs:  revenue, ebitda_margin (decimal).  Output: EBITDA.
    """
    return revenue * ebitda_margin


def calculate_ebit(ebitda: float, depreciation_amortization: float) -> float:
    """EBIT = EBITDA - D&A.

    Meaning: Operating profit after charging the wear on assets (D&A).
    Inputs:  ebitda, depreciation_amortization.  Output: EBIT.
    """
    return ebitda - depreciation_amortization


def calculate_taxes(ebit: float, tax_rate: float) -> float:
    """Taxes = EBIT * Tax Rate.

    Meaning: Cash tax on operating profit, ignoring debt (unlevered).
    Inputs:  ebit, tax_rate (decimal).  Output: Taxes on EBIT.
    """
    return ebit * tax_rate


def calculate_nopat(ebit: float, taxes: float) -> float:
    """NOPAT = EBIT - Taxes.

    Meaning: Net Operating Profit After Tax - after-tax operating earnings.
    Inputs:  ebit, taxes.  Output: NOPAT.
    """
    return ebit - taxes


def calculate_ufcf(
    nopat: float,
    depreciation_amortization: float,
    capex: float,
    change_in_nwc: float,
) -> float:
    """UFCF = NOPAT + D&A - CapEx - Change in NWC.

    Meaning: Unlevered Free Cash Flow - cash the business generates for all
    capital providers. D&A is added back because it is non-cash; CapEx and
    the increase in net working capital are real cash outflows.
    Inputs:  nopat, D&A, capex, change_in_nwc.  Output: UFCF.
    """
    return nopat + depreciation_amortization - capex - change_in_nwc


def calculate_discount_factor(wacc: float, year: int) -> float:
    """DF_t = 1 / (1 + WACC)^t.

    Meaning: Today's value of one unit received at the END of year t.
    Inputs:  wacc (decimal), year t.  Output: discount factor between 0 and 1.
    """
    return 1 / (1 + wacc) ** year


def calculate_present_value(cash_flow: float, discount_factor: float) -> float:
    """PV = Cash Flow * Discount Factor.

    Meaning: Converts a future cash flow into today's money.
    Inputs:  cash_flow, discount_factor.  Output: present value.
    """
    return cash_flow * discount_factor


def calculate_terminal_value(
    final_year_ufcf: float, wacc: float, terminal_growth: float
) -> float:
    """TV = Final Year UFCF * (1 + g) / (WACC - g)   (Gordon Growth).

    Meaning: Value, at the end of the forecast, of all cash flows after it,
    assuming they grow forever at rate g.
    Inputs:  final_year_ufcf, wacc, terminal_growth (g).
    Output:  Terminal value at the final forecast year (undiscounted).
    Raises:  ValueError if WACC <= g (formula would be meaningless).
    """
    if wacc <= terminal_growth:
        raise ValueError("WACC must be greater than terminal growth.")
    return final_year_ufcf * (1 + terminal_growth) / (wacc - terminal_growth)


def calculate_enterprise_value(sum_pv_ufcf: float, pv_terminal_value: float) -> float:
    """EV = Sum of PV(UFCF) + PV(Terminal Value).

    Meaning: Value of the whole operating business to all capital providers.
    Inputs:  sum_pv_ufcf, pv_terminal_value.  Output: enterprise value.
    """
    return sum_pv_ufcf + pv_terminal_value


def calculate_equity_value(enterprise_value: float, net_debt: float) -> float:
    """Equity Value = Enterprise Value - Net Debt.

    Meaning: What is left for shareholders after debt (net of cash) is repaid.
    Inputs:  enterprise_value, net_debt.  Output: equity value.
    """
    return enterprise_value - net_debt


def calculate_implied_share_price(equity_value: float, shares_outstanding: float) -> float:
    """Implied Share Price = Equity Value / Shares Outstanding.

    Inputs:  equity_value, shares_outstanding (> 0).  Output: value per share.
    """
    return equity_value / shares_outstanding


def calculate_upside_downside(implied_price: float, current_price: float) -> float:
    """Upside = (Implied Price - Current Price) / Current Price.

    Meaning: Percentage gap between model value and market price. Positive
    means the model value is above the market price; negative means below.
    This is arithmetic only, not an investment recommendation.
    Inputs:  implied_price, current_price (> 0).  Output: decimal (0.10 = +10%).
    """
    return (implied_price - current_price) / current_price


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_dcf(
    inputs: DCFInputs,
    historical: HistoricalData = CONTROLLED_SAMPLE_HISTORICALS,
) -> DCFResult:
    """Run the full DCF and return every intermediate and final figure.

    Steps: forecast revenue -> EBITDA -> EBIT -> taxes -> NOPAT -> UFCF ->
    discount -> terminal value -> EV -> equity value -> per-share value.
    D&A, CapEx and Change in NWC are held at their latest historical value.
    """
    da = historical.latest_depreciation_amortization
    capex = historical.latest_capex
    change_in_nwc = historical.latest_change_in_nwc

    revenues = forecast_revenue(
        historical.latest_revenue, inputs.revenue_growth, inputs.forecast_years
    )

    projections: list[YearProjection] = []
    for year, revenue in enumerate(revenues, start=1):
        ebitda = calculate_ebitda(revenue, inputs.ebitda_margin)
        ebit = calculate_ebit(ebitda, da)
        taxes = calculate_taxes(ebit, inputs.tax_rate)
        nopat = calculate_nopat(ebit, taxes)
        ufcf = calculate_ufcf(nopat, da, capex, change_in_nwc)
        discount_factor = calculate_discount_factor(inputs.wacc, year)
        projections.append(
            YearProjection(
                year=year,
                revenue=revenue,
                ebitda=ebitda,
                depreciation_amortization=da,
                ebit=ebit,
                taxes=taxes,
                nopat=nopat,
                capex=capex,
                change_in_nwc=change_in_nwc,
                ufcf=ufcf,
                discount_factor=discount_factor,
                pv_ufcf=calculate_present_value(ufcf, discount_factor),
            )
        )

    final_year = projections[-1]
    sum_pv_ufcf = sum(p.pv_ufcf for p in projections)
    terminal_value = calculate_terminal_value(
        final_year.ufcf, inputs.wacc, inputs.terminal_growth
    )
    pv_terminal_value = calculate_present_value(
        terminal_value, final_year.discount_factor
    )
    enterprise_value = calculate_enterprise_value(sum_pv_ufcf, pv_terminal_value)
    equity_value = calculate_equity_value(enterprise_value, inputs.net_debt)
    implied_share_price = calculate_implied_share_price(
        equity_value, inputs.shares_outstanding
    )

    return DCFResult(
        inputs=inputs,
        historical=historical,
        projections=tuple(projections),
        sum_pv_ufcf=sum_pv_ufcf,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal_value,
        enterprise_value=enterprise_value,
        net_debt=inputs.net_debt,
        equity_value=equity_value,
        shares_outstanding=inputs.shares_outstanding,
        implied_share_price=implied_share_price,
        current_share_price=inputs.share_price,
        upside_downside=calculate_upside_downside(
            implied_share_price, inputs.share_price
        ),
    )