"""Unit tests for backend/dcf.py.

How the expected values were obtained (so the tests do not just mirror the code):

* Year-1 figures are worked out by hand in the comments.
* Full base-case figures (years 1-5, terminal value, EV, equity value, price,
  upside) were calculated separately with exact fractional arithmetic
  (Python ``fractions.Fraction``) in a standalone script that shares no code
  with backend/dcf.py, then pasted here as constants.
* Relationship tests (reconciliations, sensitivities) check financial logic
  rather than specific numbers.

Base case (controlled sample data, Apple-style example inputs):
    latest revenue 120,000 | growth 8% | EBITDA margin 33% | tax 16%
    D&A 6,000 | CapEx 7,000 | Change in NWC 2,400 | WACC 8.5% | g 2.5%
    net debt 50,000 | shares 15,000 | current price 255
"""

from dataclasses import replace

import pytest

from backend.dcf import (
    CONTROLLED_SAMPLE_HISTORICALS,
    DCFInputs,
    HistoricalData,
    calculate_terminal_value,
    run_dcf,
)

# Tight tolerance: double-precision error on numbers of this size is ~1e-11.
REL = 1e-9
ABS = 1e-9


def approx(value: float):
    return pytest.approx(value, rel=REL, abs=ABS)


def approx_list(values: list[float]):
    return pytest.approx(values, rel=REL, abs=ABS)


# --------------------------------------------------------------------------
# Independently calculated expected values (base case)
# --------------------------------------------------------------------------

EXPECTED_REVENUE = [129600.0, 139968.0, 151165.44, 163258.6752, 176319.369216]
EXPECTED_EBITDA = [42768.0, 46189.44, 49884.5952, 53875.362816, 58185.39184128]
EXPECTED_EBIT = [36768.0, 40189.44, 43884.5952, 47875.362816, 52185.39184128]
EXPECTED_TAXES = [5882.88, 6430.3104, 7021.535232, 7660.05805056, 8349.6626946048]
EXPECTED_NOPAT = [30885.12, 33759.1296, 36863.059968, 40215.30476544, 43835.7291466752]
EXPECTED_UFCF = [27485.12, 30359.1296, 33463.059968, 36815.30476544, 40435.7291466752]
EXPECTED_DF = [
    0.9216589861751152,
    0.8494552867973412,
    0.7829080984307292,
    0.7215742842679532,
    0.6650454232884361,
]
EXPECTED_PV_UFCF = [
    25331.90783410138,
    25788.72314128565,
    26198.50064722034,
    26564.977186228934,
    26891.596606327163,
]
EXPECTED_SUM_PV_UFCF = 130775.70541516347
EXPECTED_TERMINAL_VALUE = 690777.0395890346
EXPECTED_PV_TERMINAL_VALUE = 459398.1086914224
EXPECTED_ENTERPRISE_VALUE = 590173.8141065858
EXPECTED_EQUITY_VALUE = 540173.8141065858
EXPECTED_IMPLIED_PRICE = 36.011587607105724
EXPECTED_UPSIDE = -0.8587780878152717


# --------------------------------------------------------------------------
# Helpers / fixtures
# --------------------------------------------------------------------------


def make_inputs(**overrides) -> DCFInputs:
    """Base-case inputs, optionally overriding individual fields."""
    values = dict(
        company_name="Apple Inc.",
        ticker="AAPL",
        share_price=255,
        forecast_years=5,
        revenue_growth=0.08,
        ebitda_margin=0.33,
        tax_rate=0.16,
        wacc=0.085,
        terminal_growth=0.025,
        net_debt=50000,
        shares_outstanding=15000,
    )
    values.update(overrides)
    return DCFInputs(**values)


@pytest.fixture
def result():
    return run_dcf(make_inputs())


# --------------------------------------------------------------------------
# 1-12. Core calculations against independently calculated values
# --------------------------------------------------------------------------


def test_revenue_forecast(result):
    # Hand check, year 1: 120,000 * 1.08 = 129,600
    assert result.revenue[0] == approx(129600.0)
    assert result.revenue == approx_list(EXPECTED_REVENUE)


def test_ebitda_calculation(result):
    # Hand check, year 1: 129,600 * 0.33 = 42,768
    assert result.ebitda[0] == approx(42768.0)
    assert result.ebitda == approx_list(EXPECTED_EBITDA)


def test_ebit_calculation(result):
    # Hand check, year 1: 42,768 - 6,000 = 36,768
    assert result.ebit[0] == approx(36768.0)
    assert result.ebit == approx_list(EXPECTED_EBIT)


def test_tax_calculation(result):
    # Hand check, year 1: 36,768 * 0.16 = 5,882.88
    assert result.taxes[0] == approx(5882.88)
    assert result.taxes == approx_list(EXPECTED_TAXES)


def test_nopat_calculation(result):
    # Hand check, year 1: 36,768 - 5,882.88 = 30,885.12
    assert result.nopat[0] == approx(30885.12)
    assert result.nopat == approx_list(EXPECTED_NOPAT)


def test_ufcf_calculation(result):
    # Hand check, year 1: 30,885.12 + 6,000 - 7,000 - 2,400 = 27,485.12
    assert result.ufcf[0] == approx(27485.12)
    assert result.ufcf == approx_list(EXPECTED_UFCF)


def test_discount_factor(result):
    # Hand check, year 1: 1 / 1.085 = 0.92165898...
    assert result.discount_factor[0] == approx(1 / 1.085)
    assert result.discount_factor == approx_list(EXPECTED_DF)


def test_pv_of_ufcf(result):
    assert result.pv_ufcf == approx_list(EXPECTED_PV_UFCF)
    assert result.sum_pv_ufcf == approx(EXPECTED_SUM_PV_UFCF)


def test_terminal_value(result):
    assert result.terminal_value == approx(EXPECTED_TERMINAL_VALUE)
    assert result.pv_terminal_value == approx(EXPECTED_PV_TERMINAL_VALUE)


def test_terminal_value_formula_with_hand_numbers():
    # 100 * (1 + 0.02) / (0.10 - 0.02) = 102 / 0.08 = 1,275
    assert calculate_terminal_value(100.0, 0.10, 0.02) == approx(1275.0)


def test_enterprise_value(result):
    assert result.enterprise_value == approx(EXPECTED_ENTERPRISE_VALUE)


def test_equity_value(result):
    assert result.equity_value == approx(EXPECTED_EQUITY_VALUE)


def test_implied_share_price(result):
    assert result.implied_share_price == approx(EXPECTED_IMPLIED_PRICE)


def test_upside_downside(result):
    assert result.upside_downside == approx(EXPECTED_UPSIDE)


def test_upside_is_positive_when_implied_price_exceeds_market_price():
    # Lower the market price below the model's implied price (~36.01).
    result = run_dcf(make_inputs(share_price=30))
    assert result.upside_downside == approx((EXPECTED_IMPLIED_PRICE - 30) / 30)
    assert result.upside_downside > 0


# --------------------------------------------------------------------------
# 13. Forecast horizon
# --------------------------------------------------------------------------


@pytest.mark.parametrize("years", [1, 3, 5, 10])
def test_correct_number_of_forecast_years(years):
    result = run_dcf(make_inputs(forecast_years=years))
    assert result.forecast_years == list(range(1, years + 1))
    assert len(result.revenue) == years
    assert len(result.ufcf) == years
    assert len(result.discount_factor) == years
    assert len(result.pv_ufcf) == years


# --------------------------------------------------------------------------
# Controlled sample data / simplification checks
# --------------------------------------------------------------------------


def test_controlled_sample_historical_data():
    hist = CONTROLLED_SAMPLE_HISTORICALS
    assert hist.revenue == (100000.0, 110000.0, 120000.0)
    assert hist.ebitda == (25000.0, 28000.0, 31000.0)
    assert hist.depreciation_amortization == (5000.0, 5500.0, 6000.0)
    assert hist.capex == (6000.0, 6500.0, 7000.0)
    assert hist.change_in_nwc == (2000.0, 2200.0, 2400.0)
    assert hist.latest_revenue == 120000.0


def test_da_capex_nwc_held_flat_at_latest_historical_value(result):
    assert result.depreciation_amortization == [6000.0] * 5
    assert result.capex == [7000.0] * 5
    assert result.change_in_nwc == [2400.0] * 5


def test_historical_series_must_have_equal_length():
    with pytest.raises(ValueError, match="same length"):
        HistoricalData(
            revenue=(1.0, 2.0),
            ebitda=(1.0,),
            depreciation_amortization=(1.0, 2.0),
            capex=(1.0, 2.0),
            change_in_nwc=(1.0, 2.0),
        )


# --------------------------------------------------------------------------
# 14-20. Input validation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("wacc", [0.0, -0.05])
def test_wacc_must_be_positive(wacc):
    with pytest.raises(ValueError, match="WACC must be greater than zero"):
        make_inputs(wacc=wacc, terminal_growth=0.0)


@pytest.mark.parametrize("wacc", [0.02, 0.025])  # below and equal to g = 0.025
def test_wacc_must_exceed_terminal_growth(wacc):
    with pytest.raises(ValueError, match="WACC must be greater than terminal growth"):
        make_inputs(wacc=wacc, terminal_growth=0.025)


def test_terminal_value_function_rejects_wacc_not_above_growth():
    with pytest.raises(ValueError, match="WACC must be greater than terminal growth"):
        calculate_terminal_value(100.0, 0.03, 0.03)


def test_negative_terminal_growth_rejected():
    with pytest.raises(ValueError, match="Terminal growth must not be negative"):
        make_inputs(terminal_growth=-0.01)


@pytest.mark.parametrize("tax_rate", [-0.01, 1.01])
def test_invalid_tax_rate_rejected(tax_rate):
    with pytest.raises(ValueError, match="Tax rate must be between 0 and 1"):
        make_inputs(tax_rate=tax_rate)


def test_zero_tax_rate_is_allowed_and_means_no_tax():
    result = run_dcf(make_inputs(tax_rate=0.0))
    assert result.taxes == [0.0] * 5
    assert result.nopat == approx_list(EXPECTED_EBIT)  # NOPAT = EBIT when untaxed


def test_full_tax_rate_is_allowed_and_wipes_out_nopat():
    result = run_dcf(make_inputs(tax_rate=1.0))
    assert result.nopat == [0.0] * 5
    # UFCF = 0 + 6,000 - 7,000 - 2,400 = -3,400 every year
    assert result.ufcf == approx_list([-3400.0] * 5)


@pytest.mark.parametrize("share_price", [0, -10])
def test_invalid_share_price_rejected(share_price):
    with pytest.raises(ValueError, match="Share price must be greater than zero"):
        make_inputs(share_price=share_price)


@pytest.mark.parametrize("shares", [0, -1])
def test_invalid_shares_outstanding_rejected(shares):
    with pytest.raises(ValueError, match="Shares outstanding must be greater than zero"):
        make_inputs(shares_outstanding=shares)


@pytest.mark.parametrize("years", [0, -3, 2.5])
def test_invalid_forecast_years_rejected(years):
    with pytest.raises(ValueError, match="Forecast years must be a whole number"):
        make_inputs(forecast_years=years)


def test_zero_terminal_growth_is_allowed():
    assert run_dcf(make_inputs(terminal_growth=0.0)).terminal_value > 0


# --------------------------------------------------------------------------
# Financial reconciliation tests
# --------------------------------------------------------------------------


def test_equity_value_equals_enterprise_value_minus_net_debt(result):
    assert result.equity_value == approx(result.enterprise_value - result.net_debt)
    assert result.net_debt == 50000


def test_implied_share_price_equals_equity_value_over_shares(result):
    assert result.implied_share_price == approx(
        result.equity_value / result.shares_outstanding
    )
    assert result.shares_outstanding == 15000


def test_enterprise_value_equals_pv_of_cash_flows_plus_pv_of_terminal_value(result):
    assert result.enterprise_value == approx(
        sum(result.pv_ufcf) + result.pv_terminal_value
    )


def test_pv_terminal_value_uses_final_year_discount_factor(result):
    assert result.pv_terminal_value == approx(
        result.terminal_value * result.discount_factor[-1]
    )


def test_upside_reconciles_to_prices(result):
    assert result.current_share_price == 255
    assert (1 + result.upside_downside) * result.current_share_price == approx(
        result.implied_share_price
    )


def test_terminal_value_positive_when_wacc_exceeds_growth(result):
    assert result.inputs.wacc > result.inputs.terminal_growth
    assert result.ufcf[-1] > 0
    assert result.terminal_value > 0


def test_increasing_wacc_decreases_valuation():
    base = run_dcf(make_inputs(wacc=0.085))
    higher = run_dcf(make_inputs(wacc=0.095))
    assert higher.enterprise_value < base.enterprise_value
    assert higher.implied_share_price < base.implied_share_price


def test_increasing_terminal_growth_increases_valuation():
    base = run_dcf(make_inputs(terminal_growth=0.025))
    higher = run_dcf(make_inputs(terminal_growth=0.030))
    assert higher.enterprise_value > base.enterprise_value
    assert higher.implied_share_price > base.implied_share_price


def test_increasing_revenue_growth_increases_valuation():
    base = run_dcf(make_inputs(revenue_growth=0.08))
    higher = run_dcf(make_inputs(revenue_growth=0.10))
    assert higher.enterprise_value > base.enterprise_value
    assert higher.implied_share_price > base.implied_share_price


# --------------------------------------------------------------------------
# Structured output for the future Excel generator
# --------------------------------------------------------------------------


def test_to_dict_exposes_exact_python_results(result):
    data = result.to_dict()
    expected_keys = {
        "company_name", "ticker", "forecast_years", "revenue", "ebitda",
        "depreciation_amortization", "ebit", "taxes", "nopat", "capex",
        "change_in_nwc", "ufcf", "discount_factor", "pv_ufcf", "sum_pv_ufcf",
        "terminal_value", "pv_terminal_value", "enterprise_value", "net_debt",
        "equity_value", "shares_outstanding", "implied_share_price",
        "current_share_price", "upside_downside",
    }
    assert set(data) == expected_keys
    assert data["forecast_years"] == [1, 2, 3, 4, 5]
    assert data["revenue"] == result.revenue
    assert data["enterprise_value"] == result.enterprise_value
    assert data["upside_downside"] == result.upside_downside


def test_replace_revalidates_inputs():
    # dataclasses.replace() re-runs validation, so edits cannot bypass the rules.
    with pytest.raises(ValueError, match="WACC must be greater than terminal growth"):
        replace(make_inputs(), wacc=0.01)