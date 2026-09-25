"""OSAP / Canada Student Loan repayment scenarios.

Compares standard vs accelerated amortization and the effect of extra payments.
Pure Python; educational estimates only.
"""

from __future__ import annotations

from typing import Any, Optional

from planning import DISCLAIMER
from planning.loader import load_rules


def monthly_payment(principal: float, annual_rate: float, years: float) -> float:
    """Standard amortizing loan payment (monthly compounding approximation)."""
    if principal <= 0:
        return 0.0
    n = int(round(years * 12))
    if n <= 0:
        raise ValueError("amortization years must be positive")
    if annual_rate <= 0:
        return round(principal / n, 2)
    r = annual_rate / 12.0
    payment = principal * (r * (1.0 + r) ** n) / ((1.0 + r) ** n - 1.0)
    return round(payment, 2)


def _simulate(
    principal: float,
    annual_rate: float,
    monthly_pmt: float,
    extra_monthly: float = 0.0,
    max_months: int = 600,
) -> dict[str, Any]:
    """Simulate month-by-month payoff; return totals and schedule summary."""
    if principal <= 0:
        return {
            "months": 0,
            "years": 0.0,
            "total_paid": 0.0,
            "total_interest": 0.0,
            "schedule_head": [],
        }

    balance = float(principal)
    r = annual_rate / 12.0
    total_paid = 0.0
    total_interest = 0.0
    head: list[dict[str, float]] = []
    months = 0

    while balance > 0.005 and months < max_months:
        months += 1
        interest = balance * r
        payment = monthly_pmt + max(0.0, extra_monthly)
        # Final month may be smaller than scheduled payment.
        if payment > balance + interest:
            payment = balance + interest
        principal_part = payment - interest
        if principal_part < 0:
            # Payment does not cover interest — cap runaway.
            principal_part = 0.0
            payment = interest
        balance = max(0.0, balance - principal_part)
        total_paid += payment
        total_interest += interest
        if len(head) < 3:
            head.append(
                {
                    "month": float(months),
                    "payment": round(payment, 2),
                    "interest": round(interest, 2),
                    "principal": round(principal_part, 2),
                    "balance": round(balance, 2),
                }
            )

    return {
        "months": months,
        "years": round(months / 12.0, 2),
        "total_paid": round(total_paid, 2),
        "total_interest": round(total_interest, 2),
        "schedule_head": head,
    }


def plan_osap(
    *,
    principal: float,
    annual_rate: Optional[float] = None,
    standard_years: Optional[float] = None,
    accelerated_years: Optional[float] = None,
    extra_monthly: float = 0.0,
    tax_year: int = 2026,
) -> dict[str, Any]:
    """Compare standard vs accelerated OSAP repayment, plus extra-payment effect.

    Args:
        principal: Outstanding loan balance (CAD).
        annual_rate: Override interest rate; default from rules YAML.
        standard_years: Standard amortization length; default from rules.
        accelerated_years: Shorter amortization (default: half of standard, min 2y).
        extra_monthly: Extra dollars applied each month on top of standard payment.
        tax_year: Year used to load default OSAP parameters.
    """
    if principal < 0:
        raise ValueError("principal must be >= 0")
    if extra_monthly < 0:
        raise ValueError("extra_monthly must be >= 0")

    rules = load_rules(tax_year)
    rate = float(annual_rate if annual_rate is not None else rules.osap.interest_rate)
    std_years = float(
        standard_years
        if standard_years is not None
        else rules.osap.standard_amortization_years
    )
    if accelerated_years is None:
        accelerated_years = max(2.0, std_years / 2.0)
    accel_years = float(accelerated_years)

    std_pmt = monthly_payment(principal, rate, std_years)
    accel_pmt = monthly_payment(principal, rate, accel_years)

    standard = _simulate(principal, rate, std_pmt)
    accelerated = _simulate(principal, rate, accel_pmt)
    with_extra = _simulate(principal, rate, std_pmt, extra_monthly=extra_monthly)

    interest_saved_vs_standard = round(
        standard["total_interest"] - accelerated["total_interest"], 2
    )
    interest_saved_extra = round(
        standard["total_interest"] - with_extra["total_interest"], 2
    )
    months_saved_extra = standard["months"] - with_extra["months"]

    return {
        "principal": round(principal, 2),
        "annual_interest_rate": rate,
        "standard_years": std_years,
        "accelerated_years": accel_years,
        "extra_monthly": round(extra_monthly, 2),
        "standard": {
            "monthly_payment": std_pmt,
            **standard,
        },
        "accelerated": {
            "monthly_payment": accel_pmt,
            **accelerated,
            "interest_saved_vs_standard": interest_saved_vs_standard,
            "months_saved_vs_standard": standard["months"] - accelerated["months"],
        },
        "with_extra_payments": {
            "monthly_payment": round(std_pmt + extra_monthly, 2),
            "base_payment": std_pmt,
            "extra_monthly": round(extra_monthly, 2),
            **with_extra,
            "interest_saved_vs_standard": interest_saved_extra,
            "months_saved_vs_standard": months_saved_extra,
        },
        "disclaimer": DISCLAIMER,
    }


def interest_only_first_month(principal: float, annual_rate: float) -> float:
    """Hand-check helper: first-month interest = principal * monthly rate."""
    return round(principal * (annual_rate / 12.0), 2)


def payment_formula_terms(
    principal: float, annual_rate: float, years: float
) -> dict[str, float]:
    """Expose intermediate terms for unit tests."""
    n = int(round(years * 12))
    r = annual_rate / 12.0
    if annual_rate <= 0:
        return {"n": float(n), "r": 0.0, "payment": round(principal / n, 2)}
    factor = (1.0 + r) ** n
    payment = principal * (r * factor) / (factor - 1.0)
    return {
        "n": float(n),
        "r": r,
        "factor": factor,
        "payment": round(payment, 2),
        "raw_payment": payment,
    }

