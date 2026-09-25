"""PII redaction before third-party LLMs; rehydrate for display after the call."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Match

# Placeholders: [EMAIL_1], [PHONE_1], [ACCOUNT_1], [ETRANSFER_1]
_PLACEHOLDER_RE = re.compile(
    r"\[(EMAIL|PHONE|ACCOUNT|ETRANSFER)_(\d+)\]"
)

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?1[\s\-.]?)?"
    r"(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}"
    r"(?!\d)"
)

_ACCOUNT_RE = re.compile(
    r"(?<!\d)(?:\d[ \-]?){7,18}\d(?!\d)"
)

# Prefix (group 1) + recipient name (group 2); stop before currency/amount
_ETRANSFER_RE = re.compile(
    r"(?i)((?:interac\s*)?e[-\s]?transfer(?:\s+(?:from|to|sent\s+to|received\s+from))?)"
    r"\s*[:\-]?\s*"
    r"([A-Za-z][A-Za-z\-'.]*(?:\s+[A-Za-z][A-Za-z\-'.]*)*?)"
    r"(?=\s*(?:CAD|USD|EUR|GBP|\$|\d|$))"
)


@dataclass
class RedactionMap:
    """Maps placeholders back to original PII for trusted rehydration."""

    mapping: Dict[str, str] = field(default_factory=dict)

    def remember(self, kind: str, value: str) -> str:
        for placeholder, original in self.mapping.items():
            if original == value and placeholder.startswith(f"[{kind}_"):
                return placeholder
        idx = sum(1 for k in self.mapping if k.startswith(f"[{kind}_")) + 1
        placeholder = f"[{kind}_{idx}]"
        self.mapping[placeholder] = value
        return placeholder


def _mask_account_digits(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def redact_pii(text: str, redaction_map: RedactionMap | None = None) -> tuple[str, RedactionMap]:
    """Replace emails, phones, account numbers, and e-transfer names with placeholders.

    Returns ``(redacted_text, map)``. Pass an existing map to continue across chunks.
    """
    if redaction_map is None:
        redaction_map = RedactionMap()
    if not text:
        return text, redaction_map

    out = text

    def _email(m: Match[str]) -> str:
        return redaction_map.remember("EMAIL", m.group(0))

    def _phone(m: Match[str]) -> str:
        return redaction_map.remember("PHONE", m.group(0))

    def _account(m: Match[str]) -> str:
        digits = _mask_account_digits(m.group(0))
        if len(digits) < 8:
            return m.group(0)
        return redaction_map.remember("ACCOUNT", m.group(0))

    def _etransfer(m: Match[str]) -> str:
        name = (m.group(2) or "").strip()
        if not name:
            return m.group(0)
        placeholder = redaction_map.remember("ETRANSFER", name)
        # Replace only the name span inside the full match
        name_start = m.start(2) - m.start(0)
        name_end = m.end(2) - m.start(0)
        full = m.group(0)
        return full[:name_start] + placeholder + full[name_end:]

    out = _EMAIL_RE.sub(_email, out)
    out = _PHONE_RE.sub(_phone, out)
    out = _ACCOUNT_RE.sub(_account, out)
    out = _ETRANSFER_RE.sub(_etransfer, out)
    return out, redaction_map


def rehydrate(text: str, redaction_map: RedactionMap) -> str:
    """Restore placeholders using the redaction map (trusted display path only)."""
    if not text or not redaction_map.mapping:
        return text

    def _repl(m: Match[str]) -> str:
        key = m.group(0)
        return redaction_map.mapping.get(key, key)

    return _PLACEHOLDER_RE.sub(_repl, text)
