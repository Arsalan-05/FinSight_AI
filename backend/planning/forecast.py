"""Monte Carlo cash forecast — P10/P50/P90 bands and probability of ruin.

Pure Python. Default 5,000 simulations; tests may pass a smaller ``n_sims``.
RNG is seedable for reproducibility.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any, Optional

from planning import DISCLAIMER

DEFAULT_N_SIMS = 5000


def _percentile(sorted_vals: Sequence[float], p: float) -> float:
    """Linear-interpolation percentile on a pre-sorted ascending sequence."""
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 100:
        return float(sorted_vals[-1])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)


def run_cash_forecast(
    *,
    starting_balance: float,
    monthly_income_mean: float,
    monthly_income_std: float = 0.0,
    monthly_expense_mean: float,
    monthly_expense_std: float = 0.0,
    months: int = 12,
    n_sims: int = DEFAULT_N_SIMS,
    seed: Optional[int] = None,
    ruin_threshold: float = 0.0,
) -> dict[str, Any]:
    """Run Monte Carlo cash-balance simulations.

    Each month, income and expense are drawn independently from normal
    distributions (floored at 0 for expenses; income may be 0). Ending balances
    across sims yield P10/P50/P90. P(ruin) is the fraction of sims where the
    balance fell below ``ruin_threshold`` at any month.
    """
    if months < 1:
        raise ValueError("months must be >= 1")
    if n_sims < 1:
        raise ValueError("n_sims must be >= 1")
    if monthly_income_std < 0 or monthly_expense_std < 0:
        raise ValueError("standard deviations must be >= 0")

    rng = random.Random(seed)
    ending: list[float] = []
    ruin_count = 0
    # Track path percentiles at each month for optional band series.
    month_ends: list[list[float]] = [[] for _ in range(months)]

    for _ in range(n_sims):
        bal = float(starting_balance)
        ruined = False
        for m in range(months):
            income = rng.gauss(monthly_income_mean, monthly_income_std)
            expense = rng.gauss(monthly_expense_mean, monthly_expense_std)
            if expense < 0:
                expense = 0.0
            if income < 0:
                income = 0.0
            bal += income - expense
            month_ends[m].append(bal)
            if bal < ruin_threshold:
                ruined = True
        if ruined:
            ruin_count += 1
        ending.append(bal)

    ending_sorted = sorted(ending)
    p_ruin = ruin_count / float(n_sims)

    bands_by_month: list[dict[str, float]] = []
    for m in range(months):
        col = sorted(month_ends[m])
        bands_by_month.append(
            {
                "month": m + 1,
                "p10": round(_percentile(col, 10), 2),
                "p50": round(_percentile(col, 50), 2),
                "p90": round(_percentile(col, 90), 2),
            }
        )

    return {
        "starting_balance": round(starting_balance, 2),
        "months": months,
        "n_sims": n_sims,
        "seed": seed,
        "ruin_threshold": ruin_threshold,
        "inputs": {
            "monthly_income_mean": monthly_income_mean,
            "monthly_income_std": monthly_income_std,
            "monthly_expense_mean": monthly_expense_mean,
            "monthly_expense_std": monthly_expense_std,
        },
        "ending_balance": {
            "p10": round(_percentile(ending_sorted, 10), 2),
            "p50": round(_percentile(ending_sorted, 50), 2),
            "p90": round(_percentile(ending_sorted, 90), 2),
            "mean": round(sum(ending_sorted) / len(ending_sorted), 2),
            "min": round(ending_sorted[0], 2),
            "max": round(ending_sorted[-1], 2),
        },
        "p_ruin": round(p_ruin, 6),
        "ruin_count": ruin_count,
        "bands_by_month": bands_by_month,
        "disclaimer": DISCLAIMER,
    }
