"""Tests for the deterministic Stage 6A equity-research engine."""

from __future__ import annotations

from dataclasses import replace

import pytest

from backend.equity_research import (
    CONTROLLED_SAMPLE_INPUTS,
    INLINE_TOLERANCE,
    EquityResearchInputs,
    analyse_guidance,
    analyse_metric,
    classify_guidance_revision,
    classify_surprise,
    percentage_change,
    run_equity_research,
)


def approx(value: float):
    return pytest.approx(value, rel=1e-12, abs=1e-12)


@pytest.fixture
def inputs() -> EquityResearchInputs:
    return EquityResearchInputs()


@pytest.fixture
def result(inputs):
    return run_equity_research(inputs)


# Controlled dataset -----------------------------------------------------------------

def test_controlled_sample_identity():
    assert CONTROLLED_SAMPLE_INPUTS.company_name == "Northstar Technologies plc"
    assert CONTROLLED_SAMPLE_INPUTS.ticker == "NST"
    assert CONTROLLED_SAMPLE_INPUTS.currency == "GBP"
    assert CONTROLLED_SAMPLE_INPUTS.period == "FY2026 H1"


@pytest.mark.parametrize(
    "field, expected",
    [
        ("share_price", 25.0),
        ("shares_outstanding", 200.0),
        ("net_debt", 600.0),
        ("actual_revenue", 1260.0),
        ("actual_ebitda", 300.0),
        ("actual_eps", 0.46),
        ("actual_fcf", 210.0),
        ("forward_revenue", 5200.0),
        ("forward_ebitda", 1100.0),
        ("forward_eps", 1.60),
    ],
)
def test_controlled_sample_values(field, expected):
    assert getattr(CONTROLLED_SAMPLE_INPUTS, field) == expected


# Core math --------------------------------------------------------------------------

def test_percentage_change_positive():
    assert percentage_change(110, 100) == approx(0.10)


def test_percentage_change_uses_absolute_reference_for_negative_reference():
    assert percentage_change(-80, -100) == approx(0.20)


def test_percentage_change_rejects_zero_reference():
    with pytest.raises(ValueError, match="Reference value must not be zero"):
        percentage_change(1, 0)


@pytest.mark.parametrize(
    "surprise, expected",
    [
        (INLINE_TOLERANCE + 0.0001, "BEAT"),
        (INLINE_TOLERANCE, "IN-LINE"),
        (0.0, "IN-LINE"),
        (-INLINE_TOLERANCE, "IN-LINE"),
        (-INLINE_TOLERANCE - 0.0001, "MISS"),
    ],
)
def test_classify_surprise(surprise, expected):
    assert classify_surprise(surprise) == expected


def test_classify_surprise_rejects_negative_tolerance():
    with pytest.raises(ValueError, match="Tolerance must be non-negative"):
        classify_surprise(0.1, -0.1)


@pytest.mark.parametrize(
    "revision, expected",
    [(0.01, "RAISED"), (0.0, "UNCHANGED"), (-0.01, "LOWERED")],
)
def test_classify_guidance_revision(revision, expected):
    assert classify_guidance_revision(revision) == expected


# Earnings metric analysis ------------------------------------------------------------

def test_revenue_yoy_growth(result):
    assert result.revenue.yoy_growth == approx((1260 - 1100) / 1100)


def test_revenue_surprise(result):
    assert result.revenue.surprise == approx(0.05)


def test_revenue_classification(result):
    assert result.revenue.classification == "BEAT"


def test_ebitda_yoy_growth(result):
    assert result.ebitda.yoy_growth == approx(0.25)


def test_ebitda_surprise(result):
    assert result.ebitda.surprise == approx((300 - 280) / 280)


def test_eps_yoy_growth(result):
    assert result.eps.yoy_growth == approx((0.46 - 0.36) / 0.36)


def test_eps_surprise(result):
    assert result.eps.surprise == approx((0.46 - 0.42) / 0.42)


def test_fcf_yoy_growth(result):
    assert result.fcf.yoy_growth == approx((210 - 170) / 170)


def test_fcf_surprise(result):
    assert result.fcf.surprise == approx((210 - 195) / 195)


def test_all_base_case_metrics_are_beats(result):
    assert {result.revenue.classification, result.ebitda.classification, result.eps.classification, result.fcf.classification} == {"BEAT"}


def test_analyse_metric_miss():
    metric = analyse_metric(prior=100, consensus=110, actual=100)
    assert metric.classification == "MISS"
    assert metric.surprise == approx(-10 / 110)


# Margins and cash conversion ----------------------------------------------------------

def test_prior_ebitda_margin(result):
    assert result.prior_ebitda_margin == approx(240 / 1100)


def test_consensus_ebitda_margin(result):
    assert result.consensus_ebitda_margin == approx(280 / 1200)


def test_actual_ebitda_margin(result):
    assert result.actual_ebitda_margin == approx(300 / 1260)


def test_margin_surprise(result):
    expected = (300 / 1260) - (280 / 1200)
    assert result.ebitda_margin_surprise == approx(expected)


def test_margin_surprise_bps(result):
    expected = ((300 / 1260) - (280 / 1200)) * 10000
    assert result.ebitda_margin_surprise_bps == approx(expected)


def test_margin_yoy_change_bps(result):
    expected = ((300 / 1260) - (240 / 1100)) * 10000
    assert result.ebitda_margin_yoy_change_bps == approx(expected)


def test_fcf_conversion(result):
    assert result.fcf_conversion == approx(210 / 300)


# Valuation ---------------------------------------------------------------------------

def test_market_cap(result):
    assert result.market_cap == approx(5000)


def test_enterprise_value(result):
    assert result.enterprise_value == approx(5600)


def test_forward_pe(result):
    assert result.forward_pe == approx(15.625)


def test_forward_ev_ebitda(result):
    assert result.forward_ev_ebitda == approx(5600 / 1100)


def test_forward_ev_revenue(result):
    assert result.forward_ev_revenue == approx(5600 / 5200)


def test_net_debt_ebitda(result):
    assert result.net_debt_ebitda == approx(600 / 1100)


def test_net_cash_reduces_enterprise_value(inputs):
    net_cash = run_equity_research(replace(inputs, net_debt=-400))
    assert net_cash.enterprise_value == approx(net_cash.market_cap - 400)


# Guidance ----------------------------------------------------------------------------

def test_revenue_guidance_midpoints(result):
    assert result.revenue_guidance.previous_midpoint == approx(5000)
    assert result.revenue_guidance.new_midpoint == approx(5100)


def test_revenue_guidance_revision(result):
    assert result.revenue_guidance.midpoint_revision == approx(0.02)
    assert result.revenue_guidance.classification == "RAISED"


def test_ebitda_guidance_midpoints(result):
    assert result.ebitda_guidance.previous_midpoint == approx(1040)
    assert result.ebitda_guidance.new_midpoint == approx(1090)


def test_ebitda_guidance_revision(result):
    assert result.ebitda_guidance.midpoint_revision == approx((1090 - 1040) / 1040)
    assert result.ebitda_guidance.classification == "RAISED"


def test_analyse_guidance_unchanged():
    guidance = analyse_guidance(100, 120, 100, 120)
    assert guidance.midpoint_revision == 0
    assert guidance.classification == "UNCHANGED"


def test_analyse_guidance_rejects_inverted_range():
    with pytest.raises(ValueError, match="low must not exceed"):
        analyse_guidance(120, 100, 100, 120)


# Analyst outputs ----------------------------------------------------------------------

def test_strongest_surprise_is_eps(result):
    assert result.strongest_surprise_metric == "EPS"
    assert result.strongest_surprise == approx(result.eps.surprise)


def test_scorecard_is_broad_based_beat(result):
    assert result.earnings_scorecard == "BROAD-BASED BEAT"


def test_takeaways_have_three_items(result):
    assert len(result.takeaways) == 3
    assert all(isinstance(item, str) and item.strip() for item in result.takeaways)


def test_takeaways_reference_core_analytics(result):
    joined = " ".join(result.takeaways)
    assert "consensus" in joined.lower()
    assert "margin" in joined.lower()
    assert "guidance" in joined.lower()


def test_catalysts_are_data_driven(result):
    joined = " ".join(result.catalysts).lower()
    assert "guidance" in joined
    assert "margin" in joined
    assert "cash" in joined


def test_risks_have_three_items(result):
    assert len(result.risks) == 3


def test_result_to_dict_is_structured(result):
    data = result.to_dict()
    assert data["company_name"] == "Northstar Technologies plc"
    assert data["ticker"] == "NST"
    assert data["revenue"]["classification"] == "BEAT"
    assert data["revenue_guidance"]["classification"] == "RAISED"
    assert data["market_cap"] == approx(5000)
    assert data["takeaways"] == list(result.takeaways)


# Behaviour changes --------------------------------------------------------------------

def test_lower_actual_revenue_can_turn_revenue_into_miss(inputs):
    changed = run_equity_research(replace(inputs, actual_revenue=1100))
    assert changed.revenue.classification == "MISS"


def test_lower_actual_ebitda_reduces_margin(inputs):
    changed = run_equity_research(replace(inputs, actual_ebitda=250))
    assert changed.actual_ebitda_margin < run_equity_research(inputs).actual_ebitda_margin


def test_higher_share_price_increases_market_cap_and_ev(inputs):
    base = run_equity_research(inputs)
    higher = run_equity_research(replace(inputs, share_price=30))
    assert higher.market_cap > base.market_cap
    assert higher.enterprise_value > base.enterprise_value
    assert higher.forward_pe > base.forward_pe


def test_higher_forward_ebitda_reduces_ev_ebitda(inputs):
    base = run_equity_research(inputs)
    higher = run_equity_research(replace(inputs, forward_ebitda=1200))
    assert higher.forward_ev_ebitda < base.forward_ev_ebitda


def test_lowered_guidance_is_classified_correctly(inputs):
    changed = run_equity_research(
        replace(inputs, new_revenue_guidance_low=4700, new_revenue_guidance_high=4900)
    )
    assert changed.revenue_guidance.classification == "LOWERED"


# Validation ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", ["company_name", "ticker", "currency", "period"])
def test_blank_text_fields_rejected(field):
    with pytest.raises(ValueError):
        replace(EquityResearchInputs(), **{field: "   "})


@pytest.mark.parametrize("field", ["share_price", "shares_outstanding"])
def test_nonpositive_market_inputs_rejected(field):
    with pytest.raises(ValueError):
        replace(EquityResearchInputs(), **{field: 0})


@pytest.mark.parametrize(
    "field",
    [
        "prior_revenue",
        "consensus_revenue",
        "actual_revenue",
        "prior_ebitda",
        "consensus_ebitda",
        "actual_ebitda",
        "forward_revenue",
        "forward_ebitda",
        "forward_eps",
    ],
)
def test_required_positive_financial_fields_rejected_at_zero(field):
    with pytest.raises(ValueError):
        replace(EquityResearchInputs(), **{field: 0})


@pytest.mark.parametrize("field", ["prior_eps", "consensus_eps", "prior_fcf", "consensus_fcf"])
def test_required_nonzero_reference_fields_rejected_at_zero(field):
    with pytest.raises(ValueError):
        replace(EquityResearchInputs(), **{field: 0})


@pytest.mark.parametrize(
    "low_field, high_field",
    [
        ("previous_revenue_guidance_low", "previous_revenue_guidance_high"),
        ("new_revenue_guidance_low", "new_revenue_guidance_high"),
        ("previous_ebitda_guidance_low", "previous_ebitda_guidance_high"),
        ("new_ebitda_guidance_low", "new_ebitda_guidance_high"),
    ],
)
def test_inverted_guidance_ranges_rejected(low_field, high_field):
    values = {low_field: 200, high_field: 100}
    with pytest.raises(ValueError, match="low must not exceed high"):
        replace(EquityResearchInputs(), **values)


def test_replace_revalidates_inputs(inputs):
    with pytest.raises(ValueError, match="Share price"):
        inputs.replace(share_price=0)
