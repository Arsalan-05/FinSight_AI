from __future__ import annotations

from typing import Any


def summarize_aggregate(result: dict[str, Any]) -> str:
    """Plain-English summary so small LLMs interpret tool output correctly."""
    filters = result.get("filters") or {}
    cat = filters.get("category")
    period_bits = []
    if filters.get("start_date") and filters.get("end_date"):
        period_bits.append(f"{filters['start_date']} to {filters['end_date']}")
    if filters.get("period"):
        period_bits.append(str(filters["period"]))
    when = f" ({', '.join(period_bits)})" if period_bits else ""

    if result.get("group_by") == "none":
        count = int(result.get("count", 0))
        total = float(result.get("total", 0))
        if count == 0:
            scope = f" for {cat}" if cat else ""
            return f"No transactions found{scope}{when}."
        amount = abs(total)
        scope = f" on {cat}" if cat else ""
        return (
            f"Found {count} transaction(s){scope}{when}. "
            f"Total spend: ${amount:.2f} (raw total {total:.2f})."
        )

    groups = result.get("groups") or []
    if not groups:
        return f"No spending groups found{when}."
    # Sort by absolute spend descending for "top categories" readability
    ranked = sorted(groups, key=lambda g: abs(float(g["total"])), reverse=True)
    lines = [f"Spending breakdown{when} (highest first):"]
    for g in ranked[:10]:
        label = g.get("category") or g.get("merchant") or g.get("month") or "Unknown"
        lines.append(
            f"- {label}: ${abs(float(g['total'])):.2f} ({g['count']} tx, raw {g['total']})"
        )
    return " ".join(lines)


def is_empty_aggregate(result: dict[str, Any]) -> bool:
    if result.get("group_by") == "none":
        return int(result.get("count", 0)) == 0
    return len(result.get("groups") or []) == 0
