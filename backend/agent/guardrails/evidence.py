"""Evidence IDs and [[$amount|ev_N]] tags for grounded money claims."""

from __future__ import annotations

import re
from typing import Any


_TAG_RE = re.compile(
    r"\[\[\s*\$(?P<amount>[\d,]+(?:\.\d+)?)\s*\|\s*(?P<eid>ev_\d+)\s*\]\]",
    re.IGNORECASE,
)


class EvidenceStore:
    """Sequential evidence registry for tool results in one agent turn."""

    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    def register(
        self,
        tool_name: str,
        params: dict[str, Any],
        result_dict: dict[str, Any],
        *,
        evidence_id: str | None = None,
    ) -> str:
        eid = evidence_id or f"ev_{len(self._items) + 1}"
        self._items.append(
            {
                "id": eid,
                "tool": tool_name,
                "params": params,
                "result": result_dict,
            }
        )
        return eid

    def list(self) -> list[dict[str, Any]]:
        return list(self._items)

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        for item in self._items:
            if item["id"] == evidence_id:
                return item
        return None


def format_money(amount: float, evidence_id: str) -> str:
    """Format a dollar amount as a frontend-clickable evidence tag."""
    return f"[[${float(amount):.2f}|{evidence_id}]]"


def parse_evidence_tags(text: str) -> list[dict[str, Any]]:
    """Extract evidence tags for frontend chip rendering."""
    if not text:
        return []
    tags: list[dict[str, Any]] = []
    for match in _TAG_RE.finditer(text):
        amount_raw = match.group("amount").replace(",", "")
        tags.append(
            {
                "raw": match.group(0),
                "amount": float(amount_raw),
                "evidence_id": match.group("eid"),
                "start": match.start(),
                "end": match.end(),
            }
        )
    return tags


def attach_evidence_ids_to_tool_result(
    result: dict[str, Any],
    evidence_id: str,
) -> dict[str, Any]:
    """Return a shallow copy of result with evidence_id attached."""
    attached = dict(result)
    attached["evidence_id"] = evidence_id
    return attached
