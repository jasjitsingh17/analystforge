"""Deterministic M&A / deal-execution analytics engine.

Stage 8A contains no API, frontend, Excel generation, live-data retrieval, or
LLM dependency. It is the single source of truth for the M&A workflow.

All defaults are controlled sample data for fictional companies and are
intended solely for analytical demonstration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

ACCRETION_TOLERANCE = 0.005  # +/-0.5% is treated as broadly neutral.
def _currency_symbol(currency: str) -> str:
    return {
        "GBP": "£",
        "USD": "$",
        "EUR": "€",
    }.get(currency.upper(), f"{currency.upper()} ")

@dataclass(frozen=True)
class MAExecutionInputs:
    acquirer_name: str = "Apex Systems plc"
    acquirer_ticker: str = "APX"
    target_name: str = "Meridian Analytics plc"
    target_ticker: str = "MDA"
    currency: str = "GBP"

    # Acquirer standalone financials; currency values are in millions.
    acquirer_share_price: float = 40.0
    acquirer_shares_outstanding: float = 250.0
    acquirer_net_income: float = 600.0

    # Target standalone financials; currency values are in millions.
    target_share_price: float = 20.0
    target_shares_outstanding: float = 100.0
    target_net_income: float = 120.0
    target_ltm_revenue: float = 1500.0
    target_ltm_ebitda: float = 250.0
    target_debt: float = 500.0
    target_cash: float = 200.0
    target_book_equity: float = 900.0

    # Transaction assumptions.
    offer_price_per_share: float = 25.0
    cash_consideration_pct: float = 0.50
    stock_consideration_pct: float = 0.50
    cash_on_hand_used: float = 500.0
    new_debt_interest_rate: float = 0.055
    cash_interest_rate: float = 0.020
    tax_rate: float = 0.25
    annual_pre_tax_synergies: float = 100.0

    # Simplified purchase accounting.
    identifiable_intangible_write_up: float = 300.0
    amortization_years: int = 10

    def __post_init__(self) -> None:
        text_fields = {
            "acquirer_name": self.acquirer_name,
            "acquirer_ticker": self.acquirer_ticker,
            "target_name": self.target_name,
            "target_ticker": self.target_ticker,
            "currency": self.currency,
        }
        for name, value in text_fields.items():
            if not value.strip():
                raise ValueError(f"{name} must not be blank.")

        strictly_positive = {
            "acquirer_share_price": self.acquirer_share_price,
            "acquirer_shares_outstanding": self.acquirer_shares_outstanding,
            "target_share_price": self.target_share_price,
            "target_shares_outstanding": self.target_shares_outstanding,
            "target_ltm_revenue": self.target_ltm_revenue,
            "target_ltm_ebitda": self.target_ltm_ebitda,
            "target_book_equity": self.target_book_equity,
            "offer_price_per_share": self.offer_price_per_share,
        }
        for name, value in strictly_positive.items():
            if value <= 0:
                raise ValueError(f"{name} must be greater than zero.")

        non_negative = {
            "target_debt": self.target_debt,
            "target_cash": self.target_cash,
            "cash_on_hand_used": self.cash_on_hand_used,
            "annual_pre_tax_synergies": self.annual_pre_tax_synergies,
            "identifiable_intangible_write_up": self.identifiable_intangible_write_up,
        }
        for name, value in non_negative.items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative.")

        if self.acquirer_net_income <= 0:
            raise ValueError("acquirer_net_income must be greater than zero.")
        if self.target_net_income < 0:
            raise ValueError("target_net_income must be non-negative.")

        percentage_fields = {
            "cash_consideration_pct": self.cash_consideration_pct,
            "stock_consideration_pct": self.stock_consideration_pct,
            "new_debt_interest_rate": self.new_debt_interest_rate,
            "cash_interest_rate": self.cash_interest_rate,
            "tax_rate": self.tax_rate,
        }
        for name, value in percentage_fields.items():
            if value < 0 or value > 1:
                raise ValueError(f"{name} must be between 0 and 1.")

        if abs((self.cash_consideration_pct + self.stock_consideration_pct) - 1.0) > 1e-9:
            raise ValueError("Cash and stock consideration percentages must sum to 1.0.")

        if self.tax_rate >= 1:
            raise ValueError("tax_rate must be less than 1.0.")

        if isinstance(self.amortization_years, bool) or not isinstance(self.amortization_years, int):
            raise ValueError("amortization_years must be an integer.")
        if self.amortization_years <= 0:
            raise ValueError("amortization_years must be greater than zero.")

        equity_purchase_price = self.offer_price_per_share * self.target_shares_outstanding
        cash_consideration = equity_purchase_price * self.cash_consideration_pct
        if self.cash_on_hand_used - cash_consideration > 1e-9:
            raise ValueError("cash_on_hand_used cannot exceed the cash consideration amount.")

    def replace(self, **changes: Any) -> "MAExecutionInputs":
        """Return a validated copy with selected assumptions changed."""
        return replace(self, **changes)


@dataclass(frozen=True)
class TransactionSummary:
    offer_price_per_share: float
    offer_premium: float
    equity_purchase_price: float
    target_enterprise_value: float
    target_ev_revenue: float
    target_ev_ebitda: float


@dataclass(frozen=True)
class FinancingSummary:
    cash_consideration: float
    stock_consideration: float
    cash_on_hand_used: float
    new_debt_raised: float
    new_shares_issued: float
    exchange_ratio: float
    existing_acquirer_ownership: float
    target_seller_ownership: float


@dataclass(frozen=True)
class PurchaseAccountingSummary:
    target_book_equity: float
    identifiable_intangible_write_up: float
    goodwill_created: float
    annual_incremental_amortization: float


@dataclass(frozen=True)
class AccretionDilutionSummary:
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


@dataclass(frozen=True)
class MAExecutionResult:
    inputs: MAExecutionInputs
    transaction: TransactionSummary
    financing: FinancingSummary
    purchase_accounting: PurchaseAccountingSummary
    accretion_dilution: AccretionDilutionSummary
    key_takeaways: tuple[str, ...]
    execution_risks: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "acquirer_name": self.inputs.acquirer_name,
            "acquirer_ticker": self.inputs.acquirer_ticker,
            "target_name": self.inputs.target_name,
            "target_ticker": self.inputs.target_ticker,
            "currency": self.inputs.currency,
            "transaction": asdict(self.transaction),
            "financing": asdict(self.financing),
            "purchase_accounting": asdict(self.purchase_accounting),
            "accretion_dilution": asdict(self.accretion_dilution),
            "key_takeaways": list(self.key_takeaways),
            "execution_risks": list(self.execution_risks),
        }


def percentage_change(current: float, reference: float) -> float:
    if reference == 0:
        raise ValueError("Reference value must not be zero.")
    return (current - reference) / abs(reference)


def classify_accretion(accretion_dilution: float, tolerance: float = ACCRETION_TOLERANCE) -> str:
    if tolerance < 0:
        raise ValueError("Tolerance must be non-negative.")
    if accretion_dilution > tolerance:
        return "ACCRETIVE"
    if accretion_dilution < -tolerance:
        return "DILUTIVE"
    return "NEUTRAL"


def calculate_break_even_synergies(
    *,
    acquirer_net_income: float,
    target_net_income: float,
    standalone_eps: float,
    pro_forma_shares: float,
    after_tax_financing_drag: float,
    after_tax_incremental_amortization: float,
    tax_rate: float,
) -> float:
    """Return annual pre-tax synergies required for EPS break-even.

    A negative mathematical requirement means the deal is already accretive
    before synergies. In that case the economically useful break-even value is
    floored at zero.
    """
    if standalone_eps <= 0:
        raise ValueError("standalone_eps must be greater than zero.")
    if pro_forma_shares <= 0:
        raise ValueError("pro_forma_shares must be greater than zero.")
    if tax_rate < 0 or tax_rate >= 1:
        raise ValueError("tax_rate must be between 0 and 1, exclusive of 1.")

    required_pro_forma_net_income = standalone_eps * pro_forma_shares
    required_after_tax_synergies = (
        required_pro_forma_net_income
        - acquirer_net_income
        - target_net_income
        + after_tax_financing_drag
        + after_tax_incremental_amortization
    )
    required_pre_tax_synergies = required_after_tax_synergies / (1 - tax_rate)
    return max(0.0, required_pre_tax_synergies)


def run_ma_execution(inputs: MAExecutionInputs | None = None) -> MAExecutionResult:
    """Run the deterministic controlled-sample M&A execution model."""
    i = inputs or MAExecutionInputs()

    equity_purchase_price = i.offer_price_per_share * i.target_shares_outstanding
    offer_premium = percentage_change(i.offer_price_per_share, i.target_share_price)
    target_enterprise_value = equity_purchase_price + i.target_debt - i.target_cash
    target_ev_revenue = target_enterprise_value / i.target_ltm_revenue
    target_ev_ebitda = target_enterprise_value / i.target_ltm_ebitda

    cash_consideration = equity_purchase_price * i.cash_consideration_pct
    stock_consideration = equity_purchase_price * i.stock_consideration_pct
    new_debt_raised = cash_consideration - i.cash_on_hand_used
    new_shares_issued = stock_consideration / i.acquirer_share_price
    exchange_ratio = (i.offer_price_per_share * i.stock_consideration_pct) / i.acquirer_share_price
    pro_forma_shares = i.acquirer_shares_outstanding + new_shares_issued
    existing_acquirer_ownership = i.acquirer_shares_outstanding / pro_forma_shares
    target_seller_ownership = new_shares_issued / pro_forma_shares

    annual_incremental_amortization = (
        i.identifiable_intangible_write_up / i.amortization_years
    )
    goodwill_created = (
        equity_purchase_price
        - i.target_book_equity
        - i.identifiable_intangible_write_up
    )

    standalone_eps = i.acquirer_net_income / i.acquirer_shares_outstanding
    after_tax_synergies = i.annual_pre_tax_synergies * (1 - i.tax_rate)
    after_tax_new_debt_interest = (
        new_debt_raised * i.new_debt_interest_rate * (1 - i.tax_rate)
    )
    after_tax_foregone_cash_interest = (
        i.cash_on_hand_used * i.cash_interest_rate * (1 - i.tax_rate)
    )
    after_tax_incremental_amortization = (
        annual_incremental_amortization * (1 - i.tax_rate)
    )
    after_tax_financing_drag = (
        after_tax_new_debt_interest + after_tax_foregone_cash_interest
    )

    pro_forma_net_income = (
        i.acquirer_net_income
        + i.target_net_income
        + after_tax_synergies
        - after_tax_financing_drag
        - after_tax_incremental_amortization
    )
    pro_forma_eps = pro_forma_net_income / pro_forma_shares
    accretion_dilution = percentage_change(pro_forma_eps, standalone_eps)
    classification = classify_accretion(accretion_dilution)

    break_even_pre_tax_synergies = calculate_break_even_synergies(
        acquirer_net_income=i.acquirer_net_income,
        target_net_income=i.target_net_income,
        standalone_eps=standalone_eps,
        pro_forma_shares=pro_forma_shares,
        after_tax_financing_drag=after_tax_financing_drag,
        after_tax_incremental_amortization=after_tax_incremental_amortization,
        tax_rate=i.tax_rate,
    )

    transaction = TransactionSummary(
        offer_price_per_share=i.offer_price_per_share,
        offer_premium=offer_premium,
        equity_purchase_price=equity_purchase_price,
        target_enterprise_value=target_enterprise_value,
        target_ev_revenue=target_ev_revenue,
        target_ev_ebitda=target_ev_ebitda,
    )
    financing = FinancingSummary(
        cash_consideration=cash_consideration,
        stock_consideration=stock_consideration,
        cash_on_hand_used=i.cash_on_hand_used,
        new_debt_raised=new_debt_raised,
        new_shares_issued=new_shares_issued,
        exchange_ratio=exchange_ratio,
        existing_acquirer_ownership=existing_acquirer_ownership,
        target_seller_ownership=target_seller_ownership,
    )
    purchase_accounting = PurchaseAccountingSummary(
        target_book_equity=i.target_book_equity,
        identifiable_intangible_write_up=i.identifiable_intangible_write_up,
        goodwill_created=goodwill_created,
        annual_incremental_amortization=annual_incremental_amortization,
    )
    accretion_summary = AccretionDilutionSummary(
        acquirer_standalone_eps=standalone_eps,
        pro_forma_net_income=pro_forma_net_income,
        pro_forma_shares_outstanding=pro_forma_shares,
        pro_forma_eps=pro_forma_eps,
        accretion_dilution=accretion_dilution,
        classification=classification,
        after_tax_synergies=after_tax_synergies,
        after_tax_new_debt_interest=after_tax_new_debt_interest,
        after_tax_foregone_cash_interest=after_tax_foregone_cash_interest,
        after_tax_incremental_amortization=after_tax_incremental_amortization,
        break_even_pre_tax_synergies=break_even_pre_tax_synergies,
    )

    currency_symbol = _currency_symbol(i.currency)

    key_takeaways = (
        f"Offer of {currency_symbol}{i.offer_price_per_share:.2f} implies a {offer_premium:.1%} premium to the unaffected target share price.",
        f"Transaction enterprise value is {currency_symbol}{target_enterprise_value:,.0f}m, equal to {target_ev_ebitda:.1f}x target LTM EBITDA.",
        f"Funding is {i.cash_consideration_pct:.0%} cash / {i.stock_consideration_pct:.0%} stock, with {currency_symbol}{new_debt_raised:,.0f}m of new debt raised.",
        f"Pro forma EPS is {classification.lower()} by {abs(accretion_dilution):.1%} versus acquirer standalone EPS.",
    )

    execution_risks = (
        "Synergy realization may be lower or slower than assumed.",
        "Debt-funded consideration increases financing-cost and leverage exposure.",
        "Purchase-accounting assumptions may change after detailed fair-value work.",
        "Share-price movements can alter stock consideration economics before closing.",
    )

    return MAExecutionResult(
        inputs=i,
        transaction=transaction,
        financing=financing,
        purchase_accounting=purchase_accounting,
        accretion_dilution=accretion_summary,
        key_takeaways=key_takeaways,
        execution_risks=execution_risks,
    )
