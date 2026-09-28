"""Parse transactions and balances from bank statement text (e.g. text copied out of a PDF)."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from ingest.pdf.detect import detect_bank

NormalizedTx = dict[str, Any]

_AMOUNT = re.compile(r"(?P<sign>-)?\$?\s*(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})")
_DATE = re.compile(r"(?P<d>\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}-\w{3}-\d{2,4})")
_BALANCE_LINE = re.compile(
    r"(?P<label>opening|closing|beginning|ending)\s+(?:balance)?\s*:?\s*"
    r"(?P<sign>-)?\$?\s*(?P<num>[\d,]+\.\d{2})",
    re.I,
)


def _parse_amount(raw: str) -> float:
    text = raw.strip().replace(",", "").replace("$", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    return float(text)


def _parse_date(raw: str) -> date:
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return date.fromisoformat(text[:10])


def _parse_balance_lines(text: str) -> tuple[float | None, float | None]:
    opening: float | None = None
    closing: float | None = None
    for m in _BALANCE_LINE.finditer(text):
        label = m.group("label").lower()
        num = m.group("num").replace(",", "")
        sign = -1.0 if m.group("sign") else 1.0
        value = sign * float(num)
        if label in ("opening", "beginning"):
            opening = value
        elif label in ("closing", "ending"):
            closing = value
    return opening, closing


def _parse_tx_line(line: str) -> NormalizedTx | None:
    """Parse a single statement line with date + description + amount."""
    date_m = _DATE.search(line)
    if not date_m:
        return None
    amount_matches = list(_AMOUNT.finditer(line))
    if not amount_matches:
        return None
    # Last amount on the line is usually the transaction amount (not running bal).
    amt_m = amount_matches[-1]
    amount = _parse_amount(amt_m.group(0))
    if amt_m.group("sign") is None and line[amt_m.start() :].lstrip().startswith("("):
        amount = -abs(amount)
    start = date_m.end()
    end = amt_m.start()
    desc = line[start:end].strip(" -\t|")
    if not desc or _BALANCE_LINE.search(line):
        return None
    return {
        "date": _parse_date(date_m.group("d")),
        "description": desc[:500],
        "amount": amount,
        "category": "Uncategorized",
        "merchant": None,
        "notes": None,
    }


def extract_statement_text(
    source: str | bytes,
    *,
    bank: str | None = None,
) -> dict[str, Any]:
    """Parse statement text into normalized transactions plus opening/closing balances.

    Binary PDF bytes are rejected: extract the text layer first.
    """
    if isinstance(source, bytes):
        if source[:4] == b"%PDF":
            return {
                "bank": bank or "unknown",
                "opening": None,
                "closing": None,
                "transactions": [],
                "errors": ["Binary PDF received; pass the statement's text instead."],
                "source": "text",
            }
        text = source.decode("utf-8", errors="replace")
    else:
        text = source

    detected = bank or detect_bank(text)
    opening, closing = _parse_balance_lines(text)
    txs: list[NormalizedTx] = []
    errors: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            parsed = _parse_tx_line(line)
            if parsed:
                parsed["notes"] = f"bank:{detected}"
                txs.append(parsed)
        except Exception as exc:
            errors.append(f"Line {i}: {exc}")

    return {
        "bank": detected,
        "opening": opening,
        "closing": closing,
        "transactions": txs,
        "errors": errors,
        "source": "text",
    }
