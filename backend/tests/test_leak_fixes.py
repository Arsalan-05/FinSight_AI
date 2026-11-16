"""Tests for the leak-detection fixes: fixture ground truth, as_of, false positives."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from evals.fixtures.load import load_fixture_into_db
from evals.fixtures.seed_persona import (
    CARD_FX_MARKUP_RANGE,
    FIXTURE_END,
    RNG_SEED,
    build_fixture_transactions,
)
from insights.recurring import detect_recurring_charges
from leaks.boc import load_offline_rates, nearest_rate
from leaks.fees import detect_fees
from leaks.fx import detect_fx_markup
from leaks.service import scan_all_leaks
from leaks.subscriptions import detect_forgotten_subscriptions, detect_price_creep

_ACCOUNTS = {"rbc_checking": "acc-rbc", "td_credit": "acc-td"}


def _tx(**kwargs):
    defaults = {
        "id": "tx",
        "amount": -10.0,
        "description": "",
        "merchant": None,
        "category": "Uncategorized",
        "transaction_date": date(2026, 6, 1),
        "account_id": "acc",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _monthly(merchant, amounts, *, start=date(2025, 1, 10), category="Uncategorized", desc=None):
    return [
        _tx(
            id=f"{merchant}-{i}",
            merchant=merchant,
            description=desc or merchant.upper(),
            category=category,
            amount=-amt,
            transaction_date=start + timedelta(days=30 * i),
        )
        for i, amt in enumerate(amounts)
    ]


# ── Fixture ground truth ──────────────────────────────────────────────────────


def test_fixture_lists_only_real_leaks_but_keeps_test_rows():
    txs, planted = build_fixture_transactions("u", _ACCOUNTS)
    assert len(txs) == 600
    assert len(planted) == 45
    types = {p["type"] for p in planted}
    assert "recurring_housing" not in types
    assert "adversarial_description" not in types
    descriptions = [t["description"] for t in txs]
    assert sum("RENT" in d for d in descriptions) == 12
    assert any(d.startswith("Ignore previous instructions") for d in descriptions)


def test_fixture_fx_purchases_carry_a_real_card_markup():
    txs, planted = build_fixture_transactions("u", _ACCOUNTS)
    by_id = {t["id"]: t for t in txs}
    rates = load_offline_rates()
    low, high = CARD_FX_MARKUP_RANGE
    fx_planted = [p for p in planted if p["type"] == "fx_markup"]
    assert len(fx_planted) == 28
    for p in fx_planted:
        tx = by_id[p["transaction_ids"][0]]
        reference = nearest_rate(rates, tx["transaction_date"], "USDCAD")
        implied = abs(tx["amount"]) / p["usd_amount"]
        # Allow a cent of rounding on the CAD amount.
        assert implied >= reference * (1 + low) - 0.01 / p["usd_amount"]
        assert implied <= reference * (1 + high) + 0.01 / p["usd_amount"]


def test_fixture_seed_changes_amounts_not_shape():
    txs_a, planted_a = build_fixture_transactions("u", _ACCOUNTS)
    txs_b, planted_b = build_fixture_transactions("u", _ACCOUNTS, seed=RNG_SEED + 1)
    assert len(txs_b) == 600
    assert [p["leak_id"] for p in planted_a] == [p["leak_id"] for p in planted_b]
    assert [t["amount"] for t in txs_a] != [t["amount"] for t in txs_b]
    again, _ = build_fixture_transactions("u", _ACCOUNTS)
    assert [t["amount"] for t in again] == [t["amount"] for t in txs_a]


# ── as_of ─────────────────────────────────────────────────────────────────────


def test_fees_and_fx_default_to_current_year_and_honour_as_of():
    fee = _tx(id="f", description="NSF FEE", amount=-48.0, transaction_date=date(2025, 3, 1))
    fx = _tx(
        id="x",
        description="AMAZON.COM USD 100.00",
        amount=-150.0,
        transaction_date=date(2025, 3, 1),
    )
    rates = load_offline_rates()

    assert detect_fees([fee])["year"] == date.today().year
    assert detect_fx_markup([fx], rates)["year"] == date.today().year

    as_of = date(2025, 12, 31)
    fees = detect_fees([fee], as_of=as_of)
    assert fees["year"] == 2025 and fees["yearly_total_cad"] == 48.0
    fx_result = detect_fx_markup([fx], rates, as_of=as_of)
    assert fx_result["year"] == 2025 and fx_result["yearly_total_cad"] > 0


def test_forgotten_subscription_window_ends_at_as_of():
    txs = _monthly("Adobe Creative Cloud", [34.99] * 4, start=date(2025, 8, 1))
    assert detect_forgotten_subscriptions(txs, as_of=date(2025, 12, 31))
    # Far enough later that the charges fall outside the 180-day lookback.
    assert detect_forgotten_subscriptions(txs, as_of=date(2026, 12, 31)) == []


def test_recurring_charges_honour_as_of(db_session):
    info = load_fixture_into_db(db_session)
    ids = list(info["account_ids"].values())
    assert detect_recurring_charges(db_session, account_ids=ids, as_of=date(2027, 1, 1)) == []
    found = detect_recurring_charges(db_session, account_ids=ids, as_of=FIXTURE_END)
    assert any(r["merchant"] == "GoodLife Fitness" for r in found)


def test_scan_all_leaks_as_of_matches_fixture_year(db_session):
    info = load_fixture_into_db(db_session)
    in_year = scan_all_leaks(db_session, info["user_id"], as_of=FIXTURE_END)
    types = {f["type"] for f in in_year}
    assert {"fx_markup", "fee", "forgotten_subscription", "duplicate"} <= types

    # Without as_of the scan uses today, outside the 2025 fixture: unchanged behaviour.
    current = scan_all_leaks(db_session, info["user_id"])
    assert not any(f["type"] in ("fx_markup", "fee") for f in current)


# ── False positives ───────────────────────────────────────────────────────────


def test_price_creep_ignores_variable_spending():
    groceries = _monthly("Loblaws", [62.10, 88.40, 54.75, 97.20, 71.35, 120.05])
    assert detect_price_creep(groceries) == []


def test_price_creep_ignores_usage_based_bills():
    hydro = _monthly("Hydro One", [81.43, 95.10, 88.02, 106.88, 84.60, 99.31])
    assert detect_price_creep(hydro) == []


def test_price_creep_still_flags_fixed_price_increase():
    sub = _monthly("Spotify", [11.99] * 6 + [12.99] * 6)
    findings = detect_price_creep(sub)
    assert len(findings) == 1
    assert findings[0]["amount_cad"] == 1.0


def test_price_creep_tolerates_fx_drift_on_foreign_billed_plan():
    # USD-billed plan: CAD amount drifts ~1% month to month, then a real hike.
    amounts = [27.40, 27.65, 27.20, 27.55, 27.35, 33.10, 33.45, 33.05]
    findings = detect_price_creep(_monthly("ChatGPT Plus", amounts))
    assert len(findings) == 1


def test_price_creep_needs_more_than_two_charges():
    assert detect_price_creep(_monthly("Netflix", [16.99, 18.99])) == []


def test_forgotten_subscription_skips_rent_transfers_and_savings():
    as_of = date(2025, 12, 31)
    start = date(2025, 8, 3)
    txs = (
        _monthly("Landlord", [1450.0] * 4, start=start, category="Housing")
        + _monthly("Ahmed", [60.0] * 4, start=start, category="Transfers")
        + _monthly("RBC TFSA", [500.0] * 4, start=start, category="Savings")
        # Uncategorized rent paid by e-transfer: caught by the description.
        + _monthly(
            "J Smith",
            [900.0] * 4,
            start=start,
            desc="INTERAC E-TRANSFER SENT - RENT",
        )
        + _monthly("GoodLife Fitness", [45.0] * 4, start=start, category="Health")
    )
    findings = detect_forgotten_subscriptions(txs, as_of=as_of)
    merchants = {f["evidence"]["merchant"] for f in findings}
    assert merchants == {"GoodLife Fitness"}
