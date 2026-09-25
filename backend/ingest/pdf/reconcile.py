"""Statement balance reconciliation with line-level running checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass
class ReconciliationResult:
    ok: bool
    opening: float
    closing: float
    computed_closing: float
    delta: float
    line_errors: list[str] = field(default_factory=list)
    checked_lines: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "opening": self.opening,
            "closing": self.closing,
            "computed_closing": self.computed_closing,
            "delta": self.delta,
            "line_errors": list(self.line_errors),
            "checked_lines": self.checked_lines,
        }


def _amount(tx: Any) -> float:
    if isinstance(tx, dict):
        return float(tx["amount"])
    return float(tx.amount)


def _running_balance(tx: Any) -> float | None:
    if isinstance(tx, dict):
        bal = tx.get("balance")
        return float(bal) if bal is not None else None
    bal = getattr(tx, "balance", None)
    return float(bal) if bal is not None else None


def reconcile(
    opening: float,
    txs: Sequence[Any],
    closing: float,
    *,
    tolerance: float = 0.01,
) -> ReconciliationResult:
    """Verify ``opening + sum(amounts) ≈ closing`` and optional per-line balances.

    When a transaction dict/object includes ``balance``, the running balance after
    that line must match within *tolerance*.
    """
    opening_f = float(opening)
    closing_f = float(closing)
    running = opening_f
    line_errors: list[str] = []
    checked = 0

    for i, tx in enumerate(txs, start=1):
        amt = _amount(tx)
        running = round(running + amt, 2)
        checked += 1
        expected = _running_balance(tx)
        if expected is not None and abs(running - expected) > tolerance:
            line_errors.append(
                f"Line {i}: running balance {running:.2f} != stated {expected:.2f}"
            )

    computed = round(running, 2)
    delta = round(computed - closing_f, 2)
    ok = abs(delta) <= tolerance and not line_errors
    return ReconciliationResult(
        ok=ok,
        opening=opening_f,
        closing=closing_f,
        computed_closing=computed,
        delta=delta,
        line_errors=line_errors,
        checked_lines=checked,
    )
