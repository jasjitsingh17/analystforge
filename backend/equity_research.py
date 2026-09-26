"""Deterministic equity-research earnings analysis engine.

Stage 6A deliberately contains no API, frontend, Excel, live-data retrieval, or
LLM dependency.  It is the single source of truth for the Equity Research
workflow in the same way backend/dcf.py is the source of truth for DCF.

All default data below is controlled sample data for a fictional issuer and is
not live market/company data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

INLINE_TOLERANCE = 0.005  # +/-0.5% versus consensus counts as in-line.


@dataclass(frozen=True)
class EquityResearchInputs:
    company_name: str = "Northstar Technologies plc"
    ticker: str = "NST"
    currency: str = "GBP"
    period: str = "FY2026 H1"
    share_price: float = 25.0
    shares_outstanding: float = 200.0  # millions of shares
    net_debt: float = 600.0  # currency millions; may be negative for net cash

    prior_revenue: float = 1100.0
    consensus_revenue: float = 1200.0
    actual_revenue: float = 1260.0

    prior_ebitda: float = 240.0
    consensus_ebitda: float = 280.0
    actual_ebitda: float = 300.0

    prior_eps: float = 0.36
    consensus_eps: float = 0.42
    actual_eps: float = 0.46

    prior_fcf: float = 170.0
    consensus_fcf: float = 195.0
    actual_fcf: float = 210.0

    forward_revenue: float = 5200.0
    forward_ebitda: float = 1100.0
    forward_eps: float = 1.60

    previous_revenue_guidance_low: float = 4900.0
    previous_revenue_guidance_high: float = 5100.0
    new_revenue_guidance_low: float = 5000.0
    new_revenue_guidance_high: float = 5200.0

    previous_ebitda_guidance_low: float = 1000.0
    previous_ebitda_guidance_high: float = 1080.0
    new_ebitda_guidance_low: float = 1050.0
    new_ebitda_guidance_high: float = 1130.0

    def __post_init__(self) -> None:
        if not self.company_name.strip():
            raise ValueError("Company name must not be blank.")
        if not self.ticker.strip():
            raise ValueError("Ticker must not be blank.")
        if not self.currency.strip():
            raise ValueError("Currency must not be blank.")
        if not self.period.strip():
            raise ValueError("Period must not be blank.")

        if self.share_price <= 0:
            raise ValueError("Share price must be greater than zero.")
        if self.shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be greater than zero.")

        positive_fields = {
            "prior_revenue": self.prior_revenue,
            "consensus_revenue": self.consensus_revenue,
            "actual_revenue": self.actual_revenue,
            "prior_ebitda": self.prior_ebitda,
            "consensus_ebitda": self.consensus_ebitda,
            "actual_ebitda": self.actual_ebitda,
            "forward_revenue": self.forward_revenue,
            "forward_ebitda": self.forward_ebitda,
            "forward_eps": self.forward_eps,
        }
        for name, value in positive_fields.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero.")

        nonzero_fields = {
            "prior_eps": self.prior_eps,
            "consensus_eps": self.consensus_eps,
            "prior_fcf": self.prior_fcf,
            "consensus_fcf": self.consensus_fcf,
        }
        for name, value in nonzero_fields.items():
            if value == 0:
                raise ValueError(f"{name} must not be zero.")

        guidance_pairs = {
            "previous revenue guidance": (
                self.previous_revenue_guidance_low,
                self.previous_revenue_guidance_high,
            ),
            "new revenue guidance": (
                self.new_revenue_guidance_low,
                self.new_revenue_guidance_high,
            ),
            "previous EBITDA guidance": (
                self.previous_ebitda_guidance_low,
                self.previous_ebitda_guidance_high,
            ),
            "new EBITDA guidance": (
                self.new_ebitda_guidance_low,
                self.new_ebitda_guidance_high,
            ),
        }
        for name, (low, high) in guidance_pairs.items():
            if low <= 0 or high <= 0:
                raise ValueError(f"{name} values must be greater than zero.")
            if low > high:
                raise ValueError(f"{name} low must not exceed high.")

    def replace(self, **changes: Any) -> "EquityResearchInputs":
        """Return a validated copy with selected fields changed."""
        return replace(self, **changes)


@dataclass(frozen=True)
class MetricAnalysis:
    prior: float
    consensus: float
    actual: float
    yoy_growth: float
    surprise: float
    classification: str


@dataclass(frozen=True)
class GuidanceAnalysis:
    previous_low: float
    previous_high: float
    previous_midpoint: float
    new_low: float
    new_high: float
    new_midpoint: float
    midpoint_revision: float
    classification: str


@dataclass(frozen=True)
class EquityResearchResult:
    inputs: EquityResearchInputs
    revenue: MetricAnalysis
    ebitda: MetricAnalysis
    eps: MetricAnalysis
    fcf: MetricAnalysis

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

    revenue_guidance: GuidanceAnalysis
    ebitda_guidance: GuidanceAnalysis

    strongest_surprise_metric: str
    strongest_surprise: float
    earnings_scorecard: str
    takeaways: tuple[str, ...]
    catalysts: tuple[str, ...]
    risks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly structured representation."""
        return {
            "company_name": self.inputs.company_name,
            "ticker": self.inputs.ticker,
            "currency": self.inputs.currency,
            "period": self.inputs.period,
            "share_price": self.inputs.share_price,
            "shares_outstanding": self.inputs.shares_outstanding,
            "net_debt": self.inputs.net_debt,
            "revenue": asdict(self.revenue),
            "ebitda": asdict(self.ebitda),
            "eps": asdict(self.eps),
            "fcf": asdict(self.fcf),
            "prior_ebitda_margin": self.prior_ebitda_margin,
            "consensus_ebitda_margin": self.consensus_ebitda_margin,
            "actual_ebitda_margin": self.actual_ebitda_margin,
            "ebitda_margin_surprise": self.ebitda_margin_surprise,
            "ebitda_margin_surprise_bps": self.ebitda_margin_surprise_bps,
            "ebitda_margin_yoy_change_bps": self.ebitda_margin_yoy_change_bps,
            "fcf_conversion": self.fcf_conversion,
            "market_cap": self.market_cap,
            "enterprise_value": self.enterprise_value,
            "forward_pe": self.forward_pe,
            "forward_ev_ebitda": self.forward_ev_ebitda,
            "forward_ev_revenue": self.forward_ev_revenue,
            "net_debt_ebitda": self.net_debt_ebitda,
            "revenue_guidance": asdict(self.revenue_guidance),
            "ebitda_guidance": asdict(self.ebitda_guidance),
            "strongest_surprise_metric": self.strongest_surprise_metric,
            "strongest_surprise": self.strongest_surprise,
            "earnings_scorecard": self.earnings_scorecard,
            "takeaways": list(self.takeaways),
            "catalysts": list(self.catalysts),
            "risks": list(self.risks),
        }


def percentage_change(current: float, reference: float) -> float:
    if reference == 0:
        raise ValueError("Reference value must not be zero.")
    return (current - reference) / abs(reference)


def classify_surprise(surprise: float, tolerance: float = INLINE_TOLERANCE) -> str:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative.")
    if surprise > tolerance:
        return "BEAT"
    if surprise < -tolerance:
        return "MISS"
    return "IN-LINE"


def classify_guidance_revision(revision: float, tolerance: float = INLINE_TOLERANCE) -> str:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative.")
    if revision > tolerance:
        return "RAISED"
    if revision < -tolerance:
        return "LOWERED"
    return "UNCHANGED"


def analyse_metric(prior: float, consensus: float, actual: float) -> MetricAnalysis:
    yoy = percentage_change(actual, prior)
    surprise = percentage_change(actual, consensus)
    return MetricAnalysis(
        prior=prior,
        consensus=consensus,
        actual=actual,
        yoy_growth=yoy,
        surprise=surprise,
        classification=classify_surprise(surprise),
    )


def analyse_guidance(
    previous_low: float,
    previous_high: float,
    new_low: float,
    new_high: float,
) -> GuidanceAnalysis:
    if previous_low <= 0 or previous_high <= 0 or new_low <= 0 or new_high <= 0:
        raise ValueError("Guidance values must be greater than zero.")
    if previous_low > previous_high or new_low > new_high:
        raise ValueError("Guidance low must not exceed guidance high.")

    previous_midpoint = (previous_low + previous_high) / 2
    new_midpoint = (new_low + new_high) / 2
    revision = percentage_change(new_midpoint, previous_midpoint)
    return GuidanceAnalysis(
        previous_low=previous_low,
        previous_high=previous_high,
        previous_midpoint=previous_midpoint,
        new_low=new_low,
        new_high=new_high,
        new_midpoint=new_midpoint,
        midpoint_revision=revision,
        classification=classify_guidance_revision(revision),
    )


def _format_pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:+.{decimals}f}%"


def _format_bps(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.0f} bps"


def _build_takeaways(
    inputs: EquityResearchInputs,
    revenue: MetricAnalysis,
    ebitda: MetricAnalysis,
    eps: MetricAnalysis,
    fcf: MetricAnalysis,
    margin_surprise_bps: float,
    revenue_guidance: GuidanceAnalysis,
    ebitda_guidance: GuidanceAnalysis,
) -> tuple[str, ...]:
    surprises = {
        "revenue": revenue.surprise,
        "EBITDA": ebitda.surprise,
        "EPS": eps.surprise,
        "free cash flow": fcf.surprise,
    }
    strongest_name, strongest_value = max(surprises.items(), key=lambda item: abs(item[1]))

    first = (
        f"{strongest_name.upper() if strongest_name == 'eps' else strongest_name.title()} was the "
        f"largest consensus deviation at {_format_pct(strongest_value)}, while revenue was "
        f"{_format_pct(revenue.surprise)} versus consensus and {_format_pct(revenue.yoy_growth)} year-on-year."
    )

    margin_direction = "above" if margin_surprise_bps >= 0 else "below"
    second = (
        f"EBITDA margin was {abs(margin_surprise_bps):.0f} bps {margin_direction} consensus; "
        f"EBITDA itself was {_format_pct(ebitda.surprise)} versus consensus."
    )

    third = (
        f"Revenue guidance was {revenue_guidance.classification.lower()} with a midpoint revision of "
        f"{_format_pct(revenue_guidance.midpoint_revision)}, while EBITDA guidance was "
        f"{ebitda_guidance.classification.lower()} by {_format_pct(ebitda_guidance.midpoint_revision)}."
    )

    return (first, second, third)


def _build_catalysts(
    revenue_guidance: GuidanceAnalysis,
    ebitda_guidance: GuidanceAnalysis,
    margin_surprise_bps: float,
    fcf_conversion: float,
) -> tuple[str, ...]:
    catalysts: list[str] = []
    if revenue_guidance.classification == "RAISED" or ebitda_guidance.classification == "RAISED":
        catalysts.append("Delivery against the revised revenue and EBITDA guidance ranges.")
    if margin_surprise_bps > 0:
        catalysts.append("Sustained EBITDA margin performance above the prior consensus level.")
    if fcf_conversion >= 0.60:
        catalysts.append("Continued free-cash-flow conversion relative to EBITDA.")
    if not catalysts:
        catalysts.append("Execution against current operating and cash-flow expectations.")
    return tuple(catalysts)


def _build_risks(
    revenue_guidance: GuidanceAnalysis,
    ebitda_guidance: GuidanceAnalysis,
    margin_surprise_bps: float,
) -> tuple[str, ...]:
    risks = ["A slowdown in end-demand could pressure revenue growth versus current expectations."]
    if margin_surprise_bps > 0:
        risks.append("EBITDA margin could normalize from the level achieved in the reported period.")
    else:
        risks.append("Further margin pressure could weigh on earnings delivery.")
    if revenue_guidance.classification == "RAISED" or ebitda_guidance.classification == "RAISED":
        risks.append("Higher guidance increases execution risk if trading weakens later in the forecast period.")
    else:
        risks.append("Failure to achieve the existing guidance range would weaken the earnings outlook.")
    return tuple(risks)


def run_equity_research(inputs: EquityResearchInputs) -> EquityResearchResult:
    revenue = analyse_metric(inputs.prior_revenue, inputs.consensus_revenue, inputs.actual_revenue)
    ebitda = analyse_metric(inputs.prior_ebitda, inputs.consensus_ebitda, inputs.actual_ebitda)
    eps = analyse_metric(inputs.prior_eps, inputs.consensus_eps, inputs.actual_eps)
    fcf = analyse_metric(inputs.prior_fcf, inputs.consensus_fcf, inputs.actual_fcf)

    prior_margin = inputs.prior_ebitda / inputs.prior_revenue
    consensus_margin = inputs.consensus_ebitda / inputs.consensus_revenue
    actual_margin = inputs.actual_ebitda / inputs.actual_revenue
    margin_surprise = actual_margin - consensus_margin
    margin_surprise_bps = margin_surprise * 10_000
    margin_yoy_change_bps = (actual_margin - prior_margin) * 10_000
    fcf_conversion = inputs.actual_fcf / inputs.actual_ebitda

    market_cap = inputs.share_price * inputs.shares_outstanding
    enterprise_value = market_cap + inputs.net_debt
    forward_pe = inputs.share_price / inputs.forward_eps
    forward_ev_ebitda = enterprise_value / inputs.forward_ebitda
    forward_ev_revenue = enterprise_value / inputs.forward_revenue
    net_debt_ebitda = inputs.net_debt / inputs.forward_ebitda

    revenue_guidance = analyse_guidance(
        inputs.previous_revenue_guidance_low,
        inputs.previous_revenue_guidance_high,
        inputs.new_revenue_guidance_low,
        inputs.new_revenue_guidance_high,
    )
    ebitda_guidance = analyse_guidance(
        inputs.previous_ebitda_guidance_low,
        inputs.previous_ebitda_guidance_high,
        inputs.new_ebitda_guidance_low,
        inputs.new_ebitda_guidance_high,
    )

    surprises = {
        "Revenue": revenue.surprise,
        "EBITDA": ebitda.surprise,
        "EPS": eps.surprise,
        "Free Cash Flow": fcf.surprise,
    }
    strongest_name, strongest_value = max(surprises.items(), key=lambda item: abs(item[1]))

    classifications = [revenue.classification, ebitda.classification, eps.classification, fcf.classification]
    beat_count = classifications.count("BEAT")
    miss_count = classifications.count("MISS")
    if beat_count == 4:
        scorecard = "BROAD-BASED BEAT"
    elif miss_count == 4:
        scorecard = "BROAD-BASED MISS"
    elif beat_count > miss_count:
        scorecard = "MORE BEATS THAN MISSES"
    elif miss_count > beat_count:
        scorecard = "MORE MISSES THAN BEATS"
    else:
        scorecard = "MIXED / IN-LINE"

    takeaways = _build_takeaways(
        inputs,
        revenue,
        ebitda,
        eps,
        fcf,
        margin_surprise_bps,
        revenue_guidance,
        ebitda_guidance,
    )
    catalysts = _build_catalysts(
        revenue_guidance, ebitda_guidance, margin_surprise_bps, fcf_conversion
    )
    risks = _build_risks(revenue_guidance, ebitda_guidance, margin_surprise_bps)

    return EquityResearchResult(
        inputs=inputs,
        revenue=revenue,
        ebitda=ebitda,
        eps=eps,
        fcf=fcf,
        prior_ebitda_margin=prior_margin,
        consensus_ebitda_margin=consensus_margin,
        actual_ebitda_margin=actual_margin,
        ebitda_margin_surprise=margin_surprise,
        ebitda_margin_surprise_bps=margin_surprise_bps,
        ebitda_margin_yoy_change_bps=margin_yoy_change_bps,
        fcf_conversion=fcf_conversion,
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        forward_pe=forward_pe,
        forward_ev_ebitda=forward_ev_ebitda,
        forward_ev_revenue=forward_ev_revenue,
        net_debt_ebitda=net_debt_ebitda,
        revenue_guidance=revenue_guidance,
        ebitda_guidance=ebitda_guidance,
        strongest_surprise_metric=strongest_name,
        strongest_surprise=strongest_value,
        earnings_scorecard=scorecard,
        takeaways=takeaways,
        catalysts=catalysts,
        risks=risks,
    )


CONTROLLED_SAMPLE_INPUTS = EquityResearchInputs()
