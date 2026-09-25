"""Registered-account (FHSA / TFSA / RRSP) contribution optimizer.

Pure Python year-by-year projection. Educational estimates only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from planning import DISCLAIMER
from planning.loader import PlanningRules, combined_marginal_rate, load_rules

# Prefer RRSP when combined MTR is at/above this (simplified heuristic).
_RRSP_MTR_THRESHOLD = 0.30
# Assumed annual growth inside accounts for projection (not advice).
_DEFAULT_GROWTH_RATE = 0.05


@dataclass
class ExistingRoom:
    """Unused contribution room at the start of the planning window."""

    tfsa: float = 0.0
    rrsp: float = 0.0
    fhsa: float = 0.0
    fhsa_lifetime_contributed: float = 0.0

    @classmethod
    def from_mapping(cls, data: Optional[dict[str, Any]]) -> ExistingRoom:
        data = data or {}
        return cls(
            tfsa=float(data.get("tfsa", 0) or 0),
            rrsp=float(data.get("rrsp", 0) or 0),
            fhsa=float(data.get("fhsa", 0) or 0),
            fhsa_lifetime_contributed=float(
                data.get("fhsa_lifetime_contributed", data.get("fhsa_lifetime_used", 0))
                or 0
            ),
        )


@dataclass
class YearAllocation:
    year: int
    income: float
    marginal_rate: float
    contribution_budget: float
    fhsa: float = 0.0
    tfsa: float = 0.0
    rrsp: float = 0.0
    unallocated: float = 0.0
    estimated_tax_savings: float = 0.0
    balances: dict[str, float] = field(default_factory=dict)
    room_after: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "income": round(self.income, 2),
            "marginal_rate": round(self.marginal_rate, 4),
            "contribution_budget": round(self.contribution_budget, 2),
            "fhsa": round(self.fhsa, 2),
            "tfsa": round(self.tfsa, 2),
            "rrsp": round(self.rrsp, 2),
            "unallocated": round(self.unallocated, 2),
            "estimated_tax_savings": round(self.estimated_tax_savings, 2),
            "balances": {k: round(v, 2) for k, v in self.balances.items()},
            "room_after": {k: round(v, 2) for k, v in self.room_after.items()},
        }


def _rrsp_room_for_income(income: float, rules: PlanningRules, carry: float) -> float:
    """Lesser of 18% of prior-year earned income and the RRSP dollar limit, plus carry."""
    earned_cap = max(0.0, income) * 0.18
    annual = min(earned_cap, rules.rrsp_limit)
    return max(0.0, annual + carry)


def _allocate_year(
    *,
    budget: float,
    first_time_buyer: bool,
    mtr: float,
    fhsa_room: float,
    tfsa_room: float,
    rrsp_room: float,
) -> dict[str, float]:
    """Greedy allocation: FHSA (if FTHB) → then TFSA or RRSP by MTR heuristic."""
    remaining = max(0.0, budget)
    fhsa = tfsa = rrsp = 0.0

    if first_time_buyer and fhsa_room > 0 and remaining > 0:
        fhsa = min(remaining, fhsa_room)
        remaining -= fhsa

    prefer_rrsp = mtr >= _RRSP_MTR_THRESHOLD
    order = ("rrsp", "tfsa") if prefer_rrsp else ("tfsa", "rrsp")
    rooms = {"tfsa": tfsa_room, "rrsp": rrsp_room}
    amounts = {"tfsa": 0.0, "rrsp": 0.0}
    for key in order:
        if remaining <= 0:
            break
        take = min(remaining, rooms[key])
        amounts[key] = take
        remaining -= take

    tfsa = amounts["tfsa"]
    rrsp = amounts["rrsp"]
    return {
        "fhsa": round(fhsa, 2),
        "tfsa": round(tfsa, 2),
        "rrsp": round(rrsp, 2),
        "unallocated": round(remaining, 2),
    }


def optimize_registered(
    *,
    income: float,
    age: int,
    first_time_buyer: bool,
    horizon: int,
    existing_room: Optional[dict[str, Any]] = None,
    annual_contribution: float = 0.0,
    tax_year: int = 2026,
    growth_rate: float = _DEFAULT_GROWTH_RATE,
    income_growth: float = 0.0,
    opening_balances: Optional[dict[str, float]] = None,
    rules: Optional[PlanningRules] = None,
) -> dict[str, Any]:
    """Optimize FHSA/TFSA/RRSP allocation and project year by year.

    Args:
        income: Current-year earned income (CAD).
        age: Current age (used for eligibility notes).
        first_time_buyer: If True, FHSA is considered in the priority stack.
        horizon: Number of years to project (>= 1).
        existing_room: Unused room mapping (tfsa/rrsp/fhsa/fhsa_lifetime_contributed).
        annual_contribution: Dollars available to contribute each year.
        tax_year: Starting calendar year for rules lookup.
        growth_rate: Assumed annual account growth (educational).
        income_growth: Assumed annual income growth rate.
        opening_balances: Optional starting balances per account.
        rules: Optional pre-loaded rules (tests); otherwise loaded from YAML.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if annual_contribution < 0:
        raise ValueError("annual_contribution must be >= 0")
    if income < 0:
        raise ValueError("income must be >= 0")

    room = ExistingRoom.from_mapping(existing_room)
    balances = {
        "fhsa": float((opening_balances or {}).get("fhsa", 0) or 0),
        "tfsa": float((opening_balances or {}).get("tfsa", 0) or 0),
        "rrsp": float((opening_balances or {}).get("rrsp", 0) or 0),
    }

    years: list[YearAllocation] = []
    current_income = float(income)
    tfsa_carry = max(0.0, room.tfsa)
    rrsp_carry = max(0.0, room.rrsp)
    fhsa_carry = max(0.0, room.fhsa)
    fhsa_lifetime_used = max(0.0, room.fhsa_lifetime_contributed)

    # FHSA eligibility: age 18–71 and first-time buyer (simplified).
    fhsa_eligible = first_time_buyer and 18 <= age <= 71

    for offset in range(horizon):
        year = tax_year + offset
        if rules is not None and offset == 0:
            year_rules = rules
        else:
            try:
                year_rules = load_rules(year)
            except FileNotFoundError:
                year_rules = load_rules(2026 if year >= 2026 else 2025)

        mtr = combined_marginal_rate(year_rules, current_income)

        # Annual room additions (carry unused room forward).
        tfsa_room = tfsa_carry + year_rules.tfsa_limit
        rrsp_room = _rrsp_room_for_income(current_income, year_rules, rrsp_carry)
        lifetime_left = max(0.0, year_rules.fhsa_lifetime_cap - fhsa_lifetime_used)
        annual_fhsa = year_rules.fhsa_limit + fhsa_carry if fhsa_eligible else 0.0
        fhsa_room = min(annual_fhsa, lifetime_left) if fhsa_eligible else 0.0

        alloc = _allocate_year(
            budget=annual_contribution,
            first_time_buyer=fhsa_eligible,
            mtr=mtr,
            fhsa_room=fhsa_room,
            tfsa_room=tfsa_room,
            rrsp_room=rrsp_room,
        )

        # Tax savings: deductible FHSA + RRSP contributions at current MTR.
        tax_savings = (alloc["fhsa"] + alloc["rrsp"]) * mtr

        # Grow prior balances, then add contributions.
        for key in balances:
            balances[key] = balances[key] * (1.0 + growth_rate) + alloc[key]

        fhsa_lifetime_used += alloc["fhsa"]
        tfsa_carry = max(0.0, tfsa_room - alloc["tfsa"])
        rrsp_carry = max(0.0, rrsp_room - alloc["rrsp"])
        # Unused FHSA annual room may carry up to one year of limit (simplified: full unused).
        if fhsa_eligible:
            unused_fhsa = max(0.0, fhsa_room - alloc["fhsa"])
            fhsa_carry = min(unused_fhsa, year_rules.fhsa_limit)
        else:
            fhsa_carry = 0.0

        ya = YearAllocation(
            year=year,
            income=current_income,
            marginal_rate=mtr,
            contribution_budget=annual_contribution,
            fhsa=alloc["fhsa"],
            tfsa=alloc["tfsa"],
            rrsp=alloc["rrsp"],
            unallocated=alloc["unallocated"],
            estimated_tax_savings=tax_savings,
            balances=dict(balances),
            room_after={
                "tfsa": tfsa_carry,
                "rrsp": rrsp_carry,
                "fhsa": fhsa_carry,
                "fhsa_lifetime_remaining": max(
                    0.0, year_rules.fhsa_lifetime_cap - fhsa_lifetime_used
                ),
            },
        )
        years.append(ya)
        current_income *= 1.0 + income_growth

    totals = {
        "fhsa": round(sum(y.fhsa for y in years), 2),
        "tfsa": round(sum(y.tfsa for y in years), 2),
        "rrsp": round(sum(y.rrsp for y in years), 2),
        "unallocated": round(sum(y.unallocated for y in years), 2),
        "estimated_tax_savings": round(sum(y.estimated_tax_savings for y in years), 2),
    }
    start_rules = rules if rules is not None else load_rules(tax_year)
    start_mtr = combined_marginal_rate(start_rules, income)
    if fhsa_eligible:
        priority = ["fhsa"] + (
            ["rrsp", "tfsa"] if start_mtr >= _RRSP_MTR_THRESHOLD else ["tfsa", "rrsp"]
        )
    else:
        priority = (
            ["rrsp", "tfsa"] if start_mtr >= _RRSP_MTR_THRESHOLD else ["tfsa", "rrsp"]
        )

    return {
        "tax_year": tax_year,
        "income": round(income, 2),
        "age": age,
        "first_time_buyer": first_time_buyer,
        "fhsa_eligible": fhsa_eligible,
        "horizon": horizon,
        "annual_contribution": round(annual_contribution, 2),
        "starting_marginal_rate": round(start_mtr, 4),
        "allocation_priority": priority,
        "years": [y.to_dict() for y in years],
        "totals": totals,
        "ending_balances": {k: round(v, 2) for k, v in balances.items()},
        "assumptions": {
            "growth_rate": growth_rate,
            "income_growth": income_growth,
            "rrsp_mtr_threshold": _RRSP_MTR_THRESHOLD,
            "rrsp_room": "min(18% of income, annual dollar limit) + carry-forward",
        },
        "disclaimer": DISCLAIMER,
    }


# Public alias used by tools / router.
run_registered_optimizer = optimize_registered
