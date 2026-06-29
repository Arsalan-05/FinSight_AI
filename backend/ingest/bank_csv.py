"""Detect and parse Canadian bank CSV export formats."""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Any

NormalizedRow = dict[str, Any]

# Column alias sets per bank (lowercase)
_GENERIC = {"date", "description", "amount"}
_RBC = {"transaction date", "description 1", "cad$"}
_TD = {"date", "description", "withdrawals", "deposits"}
_SCOTIA = {"date", "description", "amount"}
_BMO = {"date", "description", "amount"}
_CIBC = {"date", "description", "debit", "credit"}
_EQ = {"date", "transaction", "amount"}
_TANGERINE = {"date", "description", "amount"}
_SIMPLII = {"date", "description", "amount"}


def _norm_headers(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        return {}
    return {h.strip().lower(): h for h in fieldnames if h}


def _parse_amount(value: str) -> float:
    text = value.strip().replace(",", "").replace("$", "")
    if not text or text == "-":
        return 0.0
    # Parentheses = negative
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    return float(text)


def _parse_date(value: str) -> date:
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%d-%b-%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return date.fromisoformat(text[:10])


def _detect_bank(headers: dict[str, str]) -> str:
    keys = set(headers.keys())
    if "transaction date" in keys and "description 1" in keys:
        return "rbc"
    if "withdrawals" in keys and "deposits" in keys:
        return "td"
    if "debit" in keys and "credit" in keys and "date" in keys:
        return "cibc"
    if keys >= _GENERIC:
        inst = " ".join(keys)
        if "tangerine" in inst:
            return "tangerine"
        if "simplii" in inst:
            return "simplii"
        if "eq bank" in inst:
            return "eq"
        if "scotia" in inst or "scotiabank" in inst:
            return "scotiabank"
        if "bmo" in inst:
            return "bmo"
        return "generic"
    if "transaction" in keys and "amount" in keys:
        return "eq"
    return "unknown"


def _row_rbc(headers: dict[str, str], row: dict[str, str]) -> NormalizedRow | None:
    desc = row.get(headers.get("description 1", ""), "").strip()
    desc2 = row.get(headers.get("description 2", ""), "").strip()
    full_desc = f"{desc} {desc2}".strip() if desc2 else desc
    if not full_desc:
        return None
    amt_key = headers.get("cad$") or headers.get("amount") or headers.get("cad")
    if not amt_key:
        return None
    return {
        "date": _parse_date(row[headers["transaction date"]]),
        "description": full_desc,
        "amount": _parse_amount(row[amt_key]),
        "category": "Uncategorized",
        "merchant": None,
        "notes": "bank:rbc",
    }


def _row_td(headers: dict[str, str], row: dict[str, str]) -> NormalizedRow | None:
    desc = row.get(headers["description"], "").strip()
    if not desc:
        return None
    withdrawal = row.get(headers.get("withdrawals", ""), "").strip()
    deposit = row.get(headers.get("deposits", ""), "").strip()
    if withdrawal and withdrawal != "-":
        amount = -abs(_parse_amount(withdrawal))
    elif deposit and deposit != "-":
        amount = abs(_parse_amount(deposit))
    else:
        amount = _parse_amount(row.get(headers.get("amount", ""), "0"))
    return {
        "date": _parse_date(row[headers["date"]]),
        "description": desc,
        "amount": amount,
        "category": "Uncategorized",
        "merchant": None,
        "notes": "bank:td",
    }


def _row_debit_credit(
    headers: dict[str, str], row: dict[str, str], bank: str
) -> NormalizedRow | None:
    desc = row.get(headers["description"], "").strip()
    if not desc:
        return None
    debit = row.get(headers.get("debit", ""), "").strip()
    credit = row.get(headers.get("credit", ""), "").strip()
    if debit and debit != "-":
        amount = -abs(_parse_amount(debit))
    elif credit and credit != "-":
        amount = abs(_parse_amount(credit))
    else:
        amount = _parse_amount(row.get(headers.get("amount", ""), "0"))
    return {
        "date": _parse_date(row[headers["date"]]),
        "description": desc,
        "amount": amount,
        "category": "Uncategorized",
        "merchant": None,
        "notes": f"bank:{bank}",
    }


def _row_generic(headers: dict[str, str], row: dict[str, str], bank: str) -> NormalizedRow | None:
    desc = row.get(headers["description"], "").strip()
    if not desc:
        txn = headers.get("transaction")
        if txn:
            desc = row.get(txn, "").strip()
    if not desc:
        return None
    amt_key = headers.get("amount")
    if not amt_key:
        return None
    cat = row.get(headers.get("category", ""), "Uncategorized").strip()
    return {
        "date": _parse_date(row[headers["date"]]),
        "description": desc,
        "amount": _parse_amount(row[amt_key]),
        "category": cat or "Uncategorized",
        "merchant": row.get(headers.get("merchant", ""), "").strip() or None,
        "notes": f"bank:{bank}",
    }


def _parse_row(bank: str, headers: dict[str, str], row: dict[str, str]) -> NormalizedRow | None:
    if bank == "rbc":
        return _row_rbc(headers, row)
    if bank == "td":
        return _row_td(headers, row)
    if bank == "cibc":
        return _row_debit_credit(headers, row, "cibc")
    if bank in {"scotiabank", "bmo", "eq", "tangerine", "simplii", "generic"}:
        return _row_generic(headers, row, bank)
    return None


def detect_and_parse_csv(text: str) -> tuple[str, list[NormalizedRow], list[str]]:
    """Parse CSV text; auto-detect Canadian bank format.

    Returns (bank_id, normalized_rows, errors).
    """
    reader = csv.DictReader(io.StringIO(text))
    headers = _norm_headers(list(reader.fieldnames or []))
    if not headers:
        return "unknown", [], ["Empty or invalid CSV"]

    bank = _detect_bank(headers)

    # Standard FinSight export
    if bank == "unknown" and _GENERIC.issubset(set(headers.keys())):
        bank = "finsight"

    if bank == "finsight" or (bank == "generic" and _GENERIC.issubset(set(headers.keys()))):
        rows: list[NormalizedRow] = []
        errors: list[str] = []
        reader2 = csv.DictReader(io.StringIO(text))
        for i, row in enumerate(reader2, start=2):
            try:
                rows.append(
                    {
                        "date": _parse_date(row[headers["date"]]),
                        "description": row[headers["description"]].strip(),
                        "amount": _parse_amount(row[headers["amount"]]),
                        "category": row.get(headers.get("category", ""), "Uncategorized").strip()
                        or "Uncategorized",
                        "merchant": row.get(headers.get("merchant", ""), "").strip() or None,
                        "notes": row.get(headers.get("notes", ""), "").strip() or None,
                    }
                )
            except Exception as exc:
                errors.append(f"Row {i}: {exc}")
        return bank, rows, errors

    if bank == "unknown":
        return (
            bank,
            [],
            [
                "Unrecognized CSV format. Supported: RBC, TD, CIBC, Scotiabank, BMO, "
                "EQ Bank, Tangerine, Simplii, or standard date/description/amount."
            ],
        )

    rows = []
    errors = []
    reader3 = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader3, start=2):
        try:
            parsed = _parse_row(bank, headers, row)
            if parsed:
                rows.append(parsed)
        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    return bank, rows, errors


def guess_merchant(description: str) -> str | None:
    """Extract merchant from common Canadian transaction description patterns."""
    desc = description.strip()
    if not desc:
        return None
    # POS MERCHANT NAME CITY ON
    m = re.match(r"^(?:POS|PURCHASE|DEBIT)\s+(.+?)(?:\s+[A-Z]{2}\s*$|\s+\d{2}/\d{2})", desc, re.I)
    if m:
        return m.group(1).strip()[:80]
    return None
