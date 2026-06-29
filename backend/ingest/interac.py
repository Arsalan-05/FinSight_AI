"""Parse and normalize Canadian Interac e-Transfer transaction descriptions."""

from __future__ import annotations

import re

_INTERAC_SENT = re.compile(
    r"interac\s+e-?transfer\s+(?:sent|send)(?:\s+to\s+|\s+-\s+|\s+)(.+)",
    re.IGNORECASE,
)
_INTERAC_RECEIVED = re.compile(
    r"interac\s+e-?transfer(?:\s+received|\s+from|\s+-\s+)(?:\s+from\s+)?(.+)",
    re.IGNORECASE,
)
_INTERAC_GENERIC = re.compile(r"interac\s+e-?transfer", re.IGNORECASE)
_MEMO_SUFFIX = re.compile(r"\s*[-–]\s*memo[:\s]+(.+)$", re.IGNORECASE)


def _clean_counterparty(raw: str) -> str:
    text = raw.strip().strip('"').strip("'")
    text = _MEMO_SUFFIX.sub("", text).strip()
    # Drop trailing reference numbers
    text = re.sub(r"\s+ref[#:]?\s*\w+$", "", text, flags=re.IGNORECASE).strip()
    return text[:120] if text else "Interac Contact"


def normalize_interac_transaction(
    description: str,
    *,
    category: str = "Uncategorized",
    merchant: str | None = None,
    notes: str | None = None,
) -> tuple[str, str, str | None, str | None]:
    """Normalize Interac e-Transfer rows.

    Returns (description, category, merchant, notes).
    """
    desc = description.strip()
    if not _INTERAC_GENERIC.search(desc):
        return desc, category, merchant, notes

    counterparty = None
    direction = "transfer"

    if m := _INTERAC_SENT.search(desc):
        counterparty = _clean_counterparty(m.group(1))
        direction = "sent"
        new_desc = f"Interac e-Transfer sent to {counterparty}"
        cat = "Transfers" if category in ("Uncategorized", "") else category
    elif m := _INTERAC_RECEIVED.search(desc):
        counterparty = _clean_counterparty(m.group(1))
        direction = "received"
        new_desc = f"Interac e-Transfer from {counterparty}"
        cat = "Income" if category in ("Uncategorized", "") else category
    else:
        new_desc = "Interac e-Transfer"
        cat = category or "Transfers"

    extra = f"interac:{direction}"
    if counterparty:
        extra += f";counterparty:{counterparty}"
    merged_notes = f"{notes}; {extra}" if notes else extra

    return new_desc, cat, counterparty or merchant, merged_notes
