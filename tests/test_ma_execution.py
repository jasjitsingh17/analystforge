import math

import pytest

from backend.ma_execution import (
    ACCRETION_TOLERANCE,
    MAExecutionInputs,
    calculate_break_even_synergies,
    classify_accretion,
    percentage_change,
    run_ma_execution,
)


def test_default_inputs_are_controlled_fictional_data():
    i = MAExecutionInputs()
    assert i.acquirer_name == "Apex Systems plc"
    assert i.acquirer_ticker == "APX"
    assert i.target_name == "Meridian Analytics plc"
    assert i.target_ticker == "MDA"
    assert i.currency == "GBP"


def test_default_engine_runs():
    result = run_ma_execution()
    assert result.inputs == MAExecutionInputs()


def test_default_offer_premium():
    r = run_ma_execution()
    assert r.transaction.offer_premium == pytest.approx(0.25)


def test_default_equity_purchase_price():
    r = run_ma_execution()
    assert r.transaction.equity_purchase_price == pytest.approx(2500.0)


def test_default_target_enterprise_value():
    r = run_ma_execution()
    assert r.transaction.target_enterprise_value == pytest.approx(2800.0)


def test_default_ev_revenue():
    r = run_ma_execution()
    assert r.transaction.target_ev_revenue == pytest.approx(2800 / 1500)


def test_default_ev_ebitda():
    r = run_ma_execution()
    assert r.transaction.target_ev_ebitda == pytest.approx(11.2)


def test_default_cash_consideration():
    assert run_ma_execution().financing.cash_consideration == pytest.approx(1250.0)


def test_default_stock_consideration():
    assert run_ma_execution().financing.stock_consideration == pytest.approx(1250.0)


def test_default_new_debt_raised():
    assert run_ma_execution().financing.new_debt_raised == pytest.approx(750.0)


def test_default_new_shares_issued():
    assert run_ma_execution().financing.new_shares_issued == pytest.approx(31.25)


def test_default_exchange_ratio():
    assert run_ma_execution().financing.exchange_ratio == pytest.approx(0.3125)


def test_default_ownership_sums_to_one():
    f = run_ma_execution().financing
    assert f.existing_acquirer_ownership + f.target_seller_ownership == pytest.approx(1.0)


def test_default_existing_acquirer_ownership():
    assert run_ma_execution().financing.existing_acquirer_ownership == pytest.approx(250 / 281.25)


def test_default_target_seller_ownership():
    assert run_ma_execution().financing.target_seller_ownership == pytest.approx(31.25 / 281.25)


def test_default_goodwill():
    assert run_ma_execution().purchase_accounting.goodwill_created == pytest.approx(1300.0)


def test_default_amortization():
    assert run_ma_execution().purchase_accounting.annual_incremental_amortization == pytest.approx(30.0)


def test_default_standalone_eps():
    assert run_ma_execution().accretion_dilution.acquirer_standalone_eps == pytest.approx(2.4)


def test_default_after_tax_synergies():
    assert run_ma_execution().accretion_dilution.after_tax_synergies == pytest.approx(75.0)


def test_default_after_tax_new_debt_interest():
    expected = 750 * 0.055 * 0.75
    assert run_ma_execution().accretion_dilution.after_tax_new_debt_interest == pytest.approx(expected)


def test_default_after_tax_foregone_interest():
    assert run_ma_execution().accretion_dilution.after_tax_foregone_cash_interest == pytest.approx(7.5)


def test_default_after_tax_amortization():
    assert run_ma_execution().accretion_dilution.after_tax_incremental_amortization == pytest.approx(22.5)


def test_default_pro_forma_net_income():
    expected = 600 + 120 + 75 - (750 * 0.055 * 0.75) - 7.5 - 22.5
    assert run_ma_execution().accretion_dilution.pro_forma_net_income == pytest.approx(expected)


def test_default_pro_forma_shares():
    assert run_ma_execution().accretion_dilution.pro_forma_shares_outstanding == pytest.approx(281.25)


def test_default_pro_forma_eps():
    r = run_ma_execution().accretion_dilution
    assert r.pro_forma_eps == pytest.approx(r.pro_forma_net_income / r.pro_forma_shares_outstanding)


def test_default_deal_is_accretive():
    r = run_ma_execution().accretion_dilution
    assert r.classification == "ACCRETIVE"
    assert r.accretion_dilution > 0


def test_default_break_even_synergies_positive_and_below_assumed():
    r = run_ma_execution().accretion_dilution
    assert r.break_even_pre_tax_synergies > 0
    assert r.break_even_pre_tax_synergies < MAExecutionInputs().annual_pre_tax_synergies


def test_default_break_even_synergies_is_approximately_21_25():
    assert run_ma_execution().accretion_dilution.break_even_pre_tax_synergies == pytest.approx(21.25)


def test_to_dict_is_structured_and_json_friendly():
    d = run_ma_execution().to_dict()
    assert set(d) == {
        "acquirer_name",
        "acquirer_ticker",
        "target_name",
        "target_ticker",
        "currency",
        "transaction",
        "financing",
        "purchase_accounting",
        "accretion_dilution",
        "key_takeaways",
        "execution_risks",
    }
    assert isinstance(d["key_takeaways"], list)
    assert isinstance(d["execution_risks"], list)


def test_replace_returns_new_validated_inputs():
    original = MAExecutionInputs()
    changed = original.replace(offer_price_per_share=24.0)
    assert original.offer_price_per_share == 25.0
    assert changed.offer_price_per_share == 24.0


@pytest.mark.parametrize(
    "current,reference,expected",
    [
        (110, 100, 0.10),
        (90, 100, -0.10),
        (100, 100, 0.0),
        (-80, -100, 0.20),
    ],
)
def test_percentage_change(current, reference, expected):
    assert percentage_change(current, reference) == pytest.approx(expected)


def test_percentage_change_rejects_zero_reference():
    with pytest.raises(ValueError, match="Reference value"):
        percentage_change(1, 0)


@pytest.mark.parametrize(
    "value,expected",
    [
        (ACCRETION_TOLERANCE + 0.0001, "ACCRETIVE"),
        (ACCRETION_TOLERANCE, "NEUTRAL"),
        (0.0, "NEUTRAL"),
        (-ACCRETION_TOLERANCE, "NEUTRAL"),
        (-ACCRETION_TOLERANCE - 0.0001, "DILUTIVE"),
    ],
)
def test_classify_accretion(value, expected):
    assert classify_accretion(value) == expected


def test_classify_accretion_rejects_negative_tolerance():
    with pytest.raises(ValueError, match="Tolerance"):
        classify_accretion(0.1, tolerance=-0.01)


@pytest.mark.parametrize(
    "field",
    ["acquirer_name", "acquirer_ticker", "target_name", "target_ticker", "currency"],
)
def test_blank_text_fields_rejected(field):
    with pytest.raises(ValueError):
        MAExecutionInputs(**{field: "   "})


@pytest.mark.parametrize(
    "field",
    [
        "acquirer_share_price",
        "acquirer_shares_outstanding",
        "target_share_price",
        "target_shares_outstanding",
        "target_ltm_revenue",
        "target_ltm_ebitda",
        "target_book_equity",
        "offer_price_per_share",
    ],
)
@pytest.mark.parametrize("value", [0, -1])
def test_positive_fields_reject_nonpositive(field, value):
    with pytest.raises(ValueError):
        MAExecutionInputs(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "target_debt",
        "target_cash",
        "cash_on_hand_used",
        "annual_pre_tax_synergies",
        "identifiable_intangible_write_up",
    ],
)
def test_nonnegative_fields_reject_negative(field):
    with pytest.raises(ValueError):
        MAExecutionInputs(**{field: -0.01})


def test_acquirer_net_income_must_be_positive():
    with pytest.raises(ValueError):
        MAExecutionInputs(acquirer_net_income=0)


def test_target_net_income_may_be_zero():
    assert MAExecutionInputs(target_net_income=0).target_net_income == 0


def test_target_net_income_rejects_negative():
    with pytest.raises(ValueError):
        MAExecutionInputs(target_net_income=-1)


@pytest.mark.parametrize(
    "field",
    [
        "cash_consideration_pct",
        "stock_consideration_pct",
        "new_debt_interest_rate",
        "cash_interest_rate",
        "tax_rate",
    ],
)
@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_percentage_inputs_bounded(field, value):
    with pytest.raises(ValueError):
        MAExecutionInputs(**{field: value})


def test_consideration_mix_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        MAExecutionInputs(cash_consideration_pct=0.60, stock_consideration_pct=0.30)


def test_tax_rate_cannot_equal_one():
    with pytest.raises(ValueError, match="less than 1.0"):
        MAExecutionInputs(tax_rate=1.0)


@pytest.mark.parametrize("value", [0, -1])
def test_amortization_years_positive(value):
    with pytest.raises(ValueError):
        MAExecutionInputs(amortization_years=value)


@pytest.mark.parametrize("value", [10.0, True])
def test_amortization_years_integer(value):
    with pytest.raises(ValueError, match="integer"):
        MAExecutionInputs(amortization_years=value)


def test_cash_on_hand_cannot_exceed_cash_consideration():
    with pytest.raises(ValueError, match="cannot exceed"):
        MAExecutionInputs(cash_on_hand_used=1300.0)


def test_all_cash_deal_has_no_new_shares():
    i = MAExecutionInputs(
        cash_consideration_pct=1.0,
        stock_consideration_pct=0.0,
        cash_on_hand_used=500.0,
    )
    r = run_ma_execution(i)
    assert r.financing.new_shares_issued == pytest.approx(0.0)
    assert r.financing.target_seller_ownership == pytest.approx(0.0)
    assert r.financing.new_debt_raised == pytest.approx(2000.0)


def test_all_stock_deal_has_no_cash_or_new_debt():
    i = MAExecutionInputs(
        cash_consideration_pct=0.0,
        stock_consideration_pct=1.0,
        cash_on_hand_used=0.0,
    )
    r = run_ma_execution(i)
    assert r.financing.cash_consideration == pytest.approx(0.0)
    assert r.financing.new_debt_raised == pytest.approx(0.0)
    assert r.financing.new_shares_issued == pytest.approx(62.5)


def test_higher_offer_price_increases_purchase_price():
    low = run_ma_execution(MAExecutionInputs(offer_price_per_share=24.0))
    high = run_ma_execution(MAExecutionInputs(offer_price_per_share=30.0))
    assert high.transaction.equity_purchase_price > low.transaction.equity_purchase_price


def test_higher_offer_price_increases_offer_premium():
    low = run_ma_execution(MAExecutionInputs(offer_price_per_share=24.0))
    high = run_ma_execution(MAExecutionInputs(offer_price_per_share=30.0))
    assert high.transaction.offer_premium > low.transaction.offer_premium


def test_higher_stock_mix_increases_new_shares():
    low = run_ma_execution(MAExecutionInputs(cash_consideration_pct=0.8, stock_consideration_pct=0.2, cash_on_hand_used=500))
    high = run_ma_execution(MAExecutionInputs(cash_consideration_pct=0.2, stock_consideration_pct=0.8, cash_on_hand_used=500))
    assert high.financing.new_shares_issued > low.financing.new_shares_issued


def test_higher_cash_on_hand_reduces_new_debt():
    low_cash = run_ma_execution(MAExecutionInputs(cash_on_hand_used=100.0))
    high_cash = run_ma_execution(MAExecutionInputs(cash_on_hand_used=1000.0))
    assert high_cash.financing.new_debt_raised < low_cash.financing.new_debt_raised


def test_higher_debt_rate_reduces_pro_forma_eps():
    low = run_ma_execution(MAExecutionInputs(new_debt_interest_rate=0.03))
    high = run_ma_execution(MAExecutionInputs(new_debt_interest_rate=0.10))
    assert high.accretion_dilution.pro_forma_eps < low.accretion_dilution.pro_forma_eps


def test_higher_synergies_increase_pro_forma_eps():
    low = run_ma_execution(MAExecutionInputs(annual_pre_tax_synergies=0.0))
    high = run_ma_execution(MAExecutionInputs(annual_pre_tax_synergies=200.0))
    assert high.accretion_dilution.pro_forma_eps > low.accretion_dilution.pro_forma_eps


def test_higher_synergies_increase_accretion():
    low = run_ma_execution(MAExecutionInputs(annual_pre_tax_synergies=0.0))
    high = run_ma_execution(MAExecutionInputs(annual_pre_tax_synergies=200.0))
    assert high.accretion_dilution.accretion_dilution > low.accretion_dilution.accretion_dilution


def test_higher_intangible_write_up_increases_amortization():
    low = run_ma_execution(MAExecutionInputs(identifiable_intangible_write_up=100.0))
    high = run_ma_execution(MAExecutionInputs(identifiable_intangible_write_up=500.0))
    assert high.purchase_accounting.annual_incremental_amortization > low.purchase_accounting.annual_incremental_amortization


def test_longer_amortization_period_reduces_annual_amortization():
    short = run_ma_execution(MAExecutionInputs(amortization_years=5))
    long = run_ma_execution(MAExecutionInputs(amortization_years=15))
    assert long.purchase_accounting.annual_incremental_amortization < short.purchase_accounting.annual_incremental_amortization


def test_goodwill_can_be_negative_under_simplified_model():
    r = run_ma_execution(MAExecutionInputs(target_book_equity=2400.0, identifiable_intangible_write_up=300.0))
    assert r.purchase_accounting.goodwill_created < 0


def test_zero_synergy_case_still_runs():
    r = run_ma_execution(MAExecutionInputs(annual_pre_tax_synergies=0.0))
    assert math.isfinite(r.accretion_dilution.pro_forma_eps)


def test_break_even_is_zero_when_deal_accretive_without_synergies():
    i = MAExecutionInputs(target_net_income=250.0, annual_pre_tax_synergies=0.0)
    r = run_ma_execution(i)
    assert r.accretion_dilution.break_even_pre_tax_synergies == pytest.approx(0.0)


def test_break_even_function_rejects_bad_eps():
    with pytest.raises(ValueError):
        calculate_break_even_synergies(
            acquirer_net_income=600,
            target_net_income=120,
            standalone_eps=0,
            pro_forma_shares=280,
            after_tax_financing_drag=30,
            after_tax_incremental_amortization=20,
            tax_rate=0.25,
        )


def test_break_even_function_rejects_bad_shares():
    with pytest.raises(ValueError):
        calculate_break_even_synergies(
            acquirer_net_income=600,
            target_net_income=120,
            standalone_eps=2.4,
            pro_forma_shares=0,
            after_tax_financing_drag=30,
            after_tax_incremental_amortization=20,
            tax_rate=0.25,
        )


@pytest.mark.parametrize("tax_rate", [-0.01, 1.0, 1.1])
def test_break_even_function_rejects_bad_tax(tax_rate):
    with pytest.raises(ValueError):
        calculate_break_even_synergies(
            acquirer_net_income=600,
            target_net_income=120,
            standalone_eps=2.4,
            pro_forma_shares=280,
            after_tax_financing_drag=30,
            after_tax_incremental_amortization=20,
            tax_rate=tax_rate,
        )


def test_key_takeaways_are_deterministic():
    r1 = run_ma_execution()
    r2 = run_ma_execution()
    assert r1.key_takeaways == r2.key_takeaways


def test_execution_risks_are_deterministic():
    r1 = run_ma_execution()
    r2 = run_ma_execution()
    assert r1.execution_risks == r2.execution_risks


def test_key_takeaways_include_premium_and_funding():
    text = " ".join(run_ma_execution().key_takeaways)
    assert "premium" in text.lower()
    assert "cash" in text.lower()
    assert "stock" in text.lower()


def test_execution_risks_include_synergies_and_financing():
    text = " ".join(run_ma_execution().execution_risks).lower()
    assert "synergy" in text
    assert "debt" in text


def test_custom_names_flow_through_result():
    r = run_ma_execution(MAExecutionInputs(acquirer_name="Buyer plc", target_name="Seller plc"))
    d = r.to_dict()
    assert d["acquirer_name"] == "Buyer plc"
    assert d["target_name"] == "Seller plc"


def test_engine_is_deterministic():
    assert run_ma_execution().to_dict() == run_ma_execution().to_dict()
