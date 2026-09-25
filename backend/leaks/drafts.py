"""Template-driven action drafts for leak findings (no LLM required)."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


_CANCELLATION = """\
Subject: Cancellation request — {merchant}

Dear {merchant} Support,

I am writing to cancel my subscription effective immediately.

Account / email on file: {account_email}
Last charge: ${amount} CAD on {last_date}
Reference transaction ID(s): {transaction_ids}

Please confirm cancellation in writing and that no further charges will apply.

Thank you,
{user_name}
"""

_DISPUTE = """\
Subject: Dispute — duplicate charge of ${amount} CAD

Dear {bank_or_merchant} Disputes Team,

I am disputing a duplicate charge on my account.

Merchant: {merchant}
Amount: ${amount} CAD
Dates: {dates}
Transaction ID(s): {transaction_ids}

These appear to be duplicate charges for the same purchase within {hours_apart} hours.
Please reverse the duplicate charge of ${amount} CAD and confirm in writing.

Thank you,
{user_name}
"""

_FEE_REVERSAL = """\
Subject: Request for fee reversal — {fee_label} (${amount} CAD)

Dear {institution} Customer Service,

I am requesting a courtesy reversal of the following fee:

Fee type: {fee_label}
Amount: ${amount} CAD
Date: {date}
Description: {description}
Transaction ID: {transaction_id}

I value my relationship with {institution} and kindly ask that this fee be
reversed as a one-time courtesy. Please confirm once processed.

Thank you,
{user_name}
"""

_TEMPLATES = {
    "cancellation": _CANCELLATION,
    "dispute": _DISPUTE,
    "fee_reversal": _FEE_REVERSAL,
}

# Map finding type → default draft kind
_DEFAULT_KIND = {
    "forgotten_subscription": "cancellation",
    "subscription_creep": "cancellation",
    "duplicate": "dispute",
    "fee": "fee_reversal",
    "fx_markup": "fee_reversal",
}


def _fmt(value: Any, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value if v is not None) or default
    return str(value)


def build_draft(
    finding_type: str,
    evidence: Mapping[str, Any],
    *,
    kind: Optional[str] = None,
    user_name: str = "Account Holder",
    account_email: str = "",
    institution: str = "my bank",
) -> Dict[str, Any]:
    """
    Fill a draft template from evidence dict only (deterministic, no LLM).

    kind: cancellation | dispute | fee_reversal
    """
    draft_kind = kind or _DEFAULT_KIND.get(finding_type, "cancellation")
    template = _TEMPLATES.get(draft_kind)
    if template is None:
        raise ValueError(f"Unknown draft kind: {draft_kind}")

    fee_type = evidence.get("fee_type") or finding_type
    fee_labels = {
        "nsf": "NSF fee",
        "overdraft": "Overdraft fee",
        "e_transfer_fee": "E-Transfer fee",
        "atm_fee": "ATM fee",
        "monthly_fee": "Monthly account fee",
        "fx_markup": "FX markup / foreign transaction fee",
        "fee": "Bank fee",
    }

    fields = {
        "merchant": _fmt(evidence.get("merchant") or evidence.get("description"), "Service Provider"),
        "amount": _fmt(
            evidence.get("amount")
            or evidence.get("increase_cad")
            or evidence.get("cad_amount")
            or evidence.get("markup_cad"),
            "0.00",
        ),
        "last_date": _fmt(evidence.get("last_date") or evidence.get("date") or evidence.get("since")),
        "transaction_ids": _fmt(evidence.get("transaction_ids") or evidence.get("transaction_id")),
        "transaction_id": _fmt(evidence.get("transaction_id") or (
            (evidence.get("transaction_ids") or [None])[0]
            if isinstance(evidence.get("transaction_ids"), list)
            else evidence.get("transaction_ids")
        )),
        "dates": _fmt(evidence.get("dates")),
        "hours_apart": _fmt(evidence.get("hours_apart"), "72"),
        "description": _fmt(evidence.get("description")),
        "date": _fmt(evidence.get("date") or evidence.get("last_date")),
        "fee_label": fee_labels.get(str(fee_type), str(fee_type).replace("_", " ").title()),
        "bank_or_merchant": _fmt(
            evidence.get("institution") or evidence.get("merchant") or institution,
            institution,
        ),
        "institution": institution or "my bank",
        "user_name": user_name or "Account Holder",
        "account_email": account_email or "on file",
    }

    body = template.format(**fields)
    return {
        "kind": draft_kind,
        "finding_type": finding_type,
        "subject": body.split("\n", 1)[0].replace("Subject: ", "", 1),
        "body": body,
        "fields_used": {k: fields[k] for k in fields},
    }
