"""Student tuition tax credit estimates (clearly labeled as estimates).

Federal tuition tax credit was eliminated; Ontario still provides a provincial
credit at the lowest Ontario rate. This module produces educational estimates
only — not a tax filing calculation.
"""

from __future__ import annotations

from typing import Any, Optional

from planning import DISCLAIMER
from planning.loader import load_rules, marginal_rate

# Federal tuition amount credit was eliminated for tax years after 2016.
_FEDERAL_TUITION_CREDIT_RATE = 0.0
# Label used in responses so callers never mistake this for a filed return.
_ESTIMATE_LABEL = "ESTIMATE — not a tax filing figure"


def estimate_tuition_credit(
    *,
    eligible_tuition: float,
    province: str = "ontario",
    tax_year: int = 2026,
    carryforward_credits: float = 0.0,
) -> dict[str, Any]:
    """Estimate student tuition tax credits.

    Args:
        eligible_tuition: Eligible tuition fees paid in the year (CAD).
        province: Province for provincial credit (currently ontario only).
        tax_year: Rules year for Ontario lowest-bracket rate.
        carryforward_credits: Unused tuition amounts carried forward (CAD of
            *amounts*, converted at provincial rate for the estimate).
    """
    if eligible_tuition < 0:
        raise ValueError("eligible_tuition must be >= 0")
    if carryforward_credits < 0:
        raise ValueError("carryforward_credits must be >= 0")

    rules = load_rules(tax_year)
    province_key = province.strip().lower()
    if province_key not in {"ontario", "on"}:
        return {
            "label": _ESTIMATE_LABEL,
            "tax_year": tax_year,
            "province": province,
            "eligible_tuition": round(eligible_tuition, 2),
            "federal_credit_estimate": 0.0,
            "provincial_credit_estimate": 0.0,
            "total_credit_estimate": 0.0,
            "supported": False,
            "note": (
                f"Provincial tuition credit estimate not implemented for '{province}'. "
                "Federal tuition credit is $0 for recent tax years."
            ),
            "disclaimer": DISCLAIMER,
        }

    ontario_rate = marginal_rate(0.0, rules.ontario_brackets)
    # Ontario tuition credit ≈ lowest Ontario rate × eligible amounts.
    provincial_base = eligible_tuition + carryforward_credits
    provincial_credit = round(provincial_base * ontario_rate, 2)
    federal_credit = round(eligible_tuition * _FEDERAL_TUITION_CREDIT_RATE, 2)
    total = round(federal_credit + provincial_credit, 2)

    return {
        "label": _ESTIMATE_LABEL,
        "tax_year": tax_year,
        "province": "ontario",
        "eligible_tuition": round(eligible_tuition, 2),
        "carryforward_amounts": round(carryforward_credits, 2),
        "federal_credit_rate": _FEDERAL_TUITION_CREDIT_RATE,
        "federal_credit_estimate": federal_credit,
        "provincial_credit_rate": ontario_rate,
        "provincial_credit_estimate": provincial_credit,
        "total_credit_estimate": total,
        "supported": True,
        "note": (
            "Federal tuition tax credit eliminated after 2016. "
            "Ontario estimate uses the lowest provincial bracket rate × eligible amounts. "
            "Does not include textbooks, education amounts, or transfer to parent/spouse."
        ),
        "disclaimer": DISCLAIMER,
    }


def estimate_tuition_credit_optional(
    eligible_tuition: Optional[float],
    **kwargs: Any,
) -> dict[str, Any]:
    """Wrapper that treats None tuition as 0."""
    return estimate_tuition_credit(eligible_tuition=float(eligible_tuition or 0), **kwargs)
