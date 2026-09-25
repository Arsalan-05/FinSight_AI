"""What-if scenario overlay helper for planning engines.

Takes a base result dict and applies numeric deltas / replacements without
re-running engines unless ``recompute`` callbacks are provided.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, Callable, Optional

from planning import DISCLAIMER


def apply_overlay(
    base: Mapping[str, Any],
    overlay: Mapping[str, Any],
    *,
    recompute: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Merge ``overlay`` onto a deep copy of ``base``.

    Overlay keys:
      - ``set``: dict of absolute replacements (nested via dotted paths optional).
      - ``delta``: dict of numeric additions applied to existing numeric fields.
      - Any other top-level keys are shallow-merged into the result as metadata
        under ``scenario``.

    If ``recompute`` is provided, it receives the merged *inputs* (base inputs
    plus set/delta) and its return value becomes ``result``.
    """
    result = copy.deepcopy(dict(base))
    scenario_meta: dict[str, Any] = {
        "overlay": dict(overlay),
    }

    sets = dict(overlay.get("set") or {})
    deltas = dict(overlay.get("delta") or {})

    inputs = copy.deepcopy(result.get("inputs") or {})
    # Also allow overlays against common top-level planning fields.
    working: dict[str, Any] = {**inputs}
    for key in (
        "income",
        "annual_contribution",
        "principal",
        "extra_monthly",
        "starting_balance",
        "monthly_income_mean",
        "monthly_expense_mean",
        "horizon",
        "months",
    ):
        if key in result and key not in working:
            working[key] = result[key]

    for key, value in sets.items():
        working[key] = value
        _set_path(result, key, value)

    for key, value in deltas.items():
        current = working.get(key, result.get(key, 0))
        if not isinstance(current, (int, float)):
            current = 0
        new_val = float(current) + float(value)
        working[key] = new_val
        _set_path(result, key, new_val)

    if recompute is not None:
        recomputed = recompute(working)
        if isinstance(recomputed, dict):
            result = recomputed

    result["scenario"] = scenario_meta
    result["scenario_inputs"] = working
    result["disclaimer"] = DISCLAIMER
    return result


def what_if(
    base: Mapping[str, Any],
    *,
    set: Optional[Mapping[str, Any]] = None,  # noqa: A002 — intentional API name
    delta: Optional[Mapping[str, Any]] = None,
    recompute: Optional[Callable[[dict[str, Any]], dict[str, Any]]] = None,
    label: Optional[str] = None,
) -> dict[str, Any]:
    """Convenience wrapper around :func:`apply_overlay`."""
    overlay: dict[str, Any] = {}
    if set:
        overlay["set"] = dict(set)
    if delta:
        overlay["delta"] = dict(delta)
    if label:
        overlay["label"] = label
    out = apply_overlay(base, overlay, recompute=recompute)
    if label:
        out["scenario"]["label"] = label
    return out


def _set_path(target: dict[str, Any], key: str, value: Any) -> None:
    """Set ``key`` on ``target``; supports one level of ``a.b`` nesting."""
    if "." not in key:
        target[key] = value
        if "inputs" in target and isinstance(target["inputs"], dict) and key in target["inputs"]:
            target["inputs"][key] = value
        return
    head, tail = key.split(".", 1)
    node = target.setdefault(head, {})
    if not isinstance(node, dict):
        target[head] = {tail: value}
        return
    node[tail] = value
