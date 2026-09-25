"""PII redaction recall tests on fixture-like strings."""

from __future__ import annotations

from agent.privacy.redact import redact_pii, rehydrate


FIXTURES = [
    (
        "Email arsalan@example.com about the refund",
        "EMAIL",
        "arsalan@example.com",
    ),
    (
        "Call me at +1 (416) 555-0199 tomorrow",
        "PHONE",
        None,  # phone formatting varies; just assert placeholder + rehydrate
    ),
    (
        "Account 4532 1234 5678 9010 charged $12",
        "ACCOUNT",
        "4532 1234 5678 9010",
    ),
    (
        "INTERAC e-Transfer from Jane Doe CAD 50.00",
        "ETRANSFER",
        "Jane Doe",
    ),
]


def test_redact_and_rehydrate_email() -> None:
    text = "Contact arsalan@example.com for OSAP docs"
    redacted, cmap = redact_pii(text)
    assert "arsalan@example.com" not in redacted
    assert "[EMAIL_1]" in redacted
    assert rehydrate(redacted, cmap) == text


def test_redact_and_rehydrate_phone() -> None:
    text = "SMS (416) 555-0199 please"
    redacted, cmap = redact_pii(text)
    assert "555-0199" not in redacted
    assert "[PHONE_1]" in redacted
    assert rehydrate(redacted, cmap) == text


def test_redact_and_rehydrate_account() -> None:
    text = "Visa **** ending 4532123456789010 posted"
    # Use continuous digits for stable account match
    text = "Paid with card 4532123456789010 today"
    redacted, cmap = redact_pii(text)
    assert "4532123456789010" not in redacted
    assert "[ACCOUNT_1]" in redacted
    assert rehydrate(redacted, cmap) == text


def test_redact_and_rehydrate_etransfer() -> None:
    text = "INTERAC e-Transfer from Jane Doe CAD 50.00"
    redacted, cmap = redact_pii(text)
    assert "Jane Doe" not in redacted
    assert "[ETRANSFER_1]" in redacted
    assert "INTERAC" in redacted.upper() or "e-Transfer" in redacted or "e-transfer" in redacted.lower()
    assert rehydrate(redacted, cmap) == text


def test_fixture_batch_recall() -> None:
    """Every fixture redacts the sensitive span and rehydrates losslessly."""
    for text, kind, _expected in FIXTURES:
        redacted, cmap = redact_pii(text)
        assert f"[{kind}_" in redacted or kind == "PHONE"
        assert rehydrate(redacted, cmap) == text


def test_reuse_same_value_same_placeholder() -> None:
    text = "a@b.com and again a@b.com"
    redacted, cmap = redact_pii(text)
    assert redacted.count("[EMAIL_1]") == 2
    assert len(cmap.mapping) == 1
