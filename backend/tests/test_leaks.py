"""Planted-leak precision tests for the money-leak engine."""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from leaks.boc import load_offline_rates, nearest_rate
from leaks.drafts import build_draft
from leaks.duplicates import detect_duplicates
from leaks.fees import classify_fee, detect_fees
from leaks.fx import detect_fx_markup, parse_foreign_amount
from leaks.subscriptions import detect_forgotten_subscriptions, detect_price_creep
from db.models import Account, LeakFinding, Transaction, User
from leaks.service import scan_all_leaks, upsert_findings


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


# ── FX markup ─────────────────────────────────────────────────────────────────


def test_parse_foreign_amount_variants():
    assert parse_foreign_amount("AMAZON.COM USD 49.99") == ("USD", 49.99)
    assert parse_foreign_amount("Hotel booking 120.00 EUR") == ("EUR", 120.0)
    assert parse_foreign_amount("Purchase $35.50 USD") == ("USD", 35.50)
    assert parse_foreign_amount("LOCAL CAD purchase") is None


def test_fx_markup_detects_planted_leak():
    rates = load_offline_rates()
    # BoC USDCAD on 2026-06-01 = 1.38; charge at 1.45 implied
    foreign = 100.0
    cad = round(foreign * 1.45, 2)  # 145.00
    txs = [
        _tx(
            id="fx1",
            description="APPLE.COM/BILL USD 100.00",
            amount=-cad,
            transaction_date=date(2026, 6, 1),
        )
    ]
    result = detect_fx_markup(txs, rates, year=2026)
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["type"] == "fx_markup"
    assert item["amount_cad"] == round(145.0 - 100.0 * 1.38, 2)
    assert result["yearly_total_cad"] == item["amount_cad"]
    assert item["evidence"]["unverifiable"] is False


def test_fx_unverifiable_when_foreign_amount_missing():
    rates = load_offline_rates()
    txs = [
        _tx(
            id="fx2",
            description="FOREIGN EXCHANGE PURCHASE AMAZON",
            amount=-80.0,
            transaction_date=date(2026, 6, 1),
        )
    ]
    result = detect_fx_markup(txs, rates, year=2026)
    assert result["items"] == []
    assert len(result["unverifiable"]) == 1
    assert result["unverifiable"][0]["evidence"]["reason"] == "foreign_amount_missing"
    assert result["yearly_total_cad"] == 0.0


def test_fx_no_false_positive_at_boc_rate():
    rates = load_offline_rates()
    boc = nearest_rate(rates, date(2026, 6, 1), "USDCAD")
    assert boc is not None
    txs = [
        _tx(
            id="fx3",
            description="NETFLIX USD 15.00",
            amount=-round(15.0 * boc, 2),
            transaction_date=date(2026, 6, 1),
        )
    ]
    result = detect_fx_markup(txs, rates, year=2026)
    assert result["items"] == []


# ── Duplicates ────────────────────────────────────────────────────────────────


def test_duplicate_within_72h():
    d0 = date(2026, 4, 10)
    txs = [
        _tx(id="d1", merchant="Best Buy", amount=-199.99, transaction_date=d0),
        _tx(
            id="d2",
            merchant="Best Buy",
            amount=-199.99,
            transaction_date=d0 + timedelta(days=1),
        ),
    ]
    findings = detect_duplicates(txs)
    assert len(findings) == 1
    assert findings[0]["type"] == "duplicate"
    assert findings[0]["amount_cad"] == 199.99
    assert findings[0]["evidence"]["confidence"] >= 0.7


def test_duplicate_excludes_recurring_merchants():
    d0 = date(2026, 4, 10)
    txs = [
        _tx(id="d3", merchant="Spotify", amount=-11.99, transaction_date=d0),
        _tx(
            id="d4",
            merchant="Spotify",
            amount=-11.99,
            transaction_date=d0 + timedelta(days=1),
        ),
    ]
    findings = detect_duplicates(txs, recurring_merchants=["Spotify"])
    assert findings == []


def test_duplicate_outside_72h_ignored():
    d0 = date(2026, 4, 10)
    txs = [
        _tx(id="d5", merchant="IKEA", amount=-50.0, transaction_date=d0),
        _tx(
            id="d6",
            merchant="IKEA",
            amount=-50.0,
            transaction_date=d0 + timedelta(days=5),
        ),
    ]
    assert detect_duplicates(txs) == []


# ── Fees ──────────────────────────────────────────────────────────────────────


def test_fee_classifier_types():
    assert classify_fee("NSF FEE CHARGE") == "nsf"
    assert classify_fee("OVERDRAFT INTEREST") == "overdraft"
    assert classify_fee("MONTHLY ACCOUNT FEE") == "monthly_fee"
    assert classify_fee("INTERAC E-TRANSFER FEE") == "e_transfer_fee"
    assert classify_fee("ATM FEE OUT OF NETWORK") == "atm_fee"
    assert classify_fee("GROCERY STORE") is None


def test_fee_yearly_total_planted():
    txs = [
        _tx(
            id="f1",
            description="NSF FEE",
            amount=-45.0,
            transaction_date=date(2026, 2, 1),
        ),
        _tx(
            id="f2",
            description="MONTHLY ACCOUNT FEE",
            amount=-15.95,
            transaction_date=date(2026, 3, 1),
        ),
        _tx(
            id="f3",
            description="ATM FEE",
            amount=-3.0,
            transaction_date=date(2026, 3, 15),
        ),
        # Prior year — excluded from yearly when year=2026
        _tx(
            id="f4",
            description="NSF FEE",
            amount=-45.0,
            transaction_date=date(2025, 12, 1),
        ),
    ]
    result = detect_fees(txs, year=2026)
    assert result["yearly_total_cad"] == round(45.0 + 15.95 + 3.0, 2)
    assert result["by_type"]["nsf"] == 45.0
    assert len(result["items"]) == 3


# ── Subscriptions ─────────────────────────────────────────────────────────────


def test_price_creep_detection():
    txs = [
        _tx(
            id="s1",
            merchant="Netflix",
            amount=-16.99,
            transaction_date=date(2026, 1, 5),
        ),
        _tx(
            id="s2",
            merchant="Netflix",
            amount=-16.99,
            transaction_date=date(2026, 2, 5),
        ),
        _tx(
            id="s3",
            merchant="Netflix",
            amount=-18.99,
            transaction_date=date(2026, 3, 5),
        ),
        _tx(
            id="s4",
            merchant="Netflix",
            amount=-18.99,
            transaction_date=date(2026, 4, 5),
        ),
    ]
    findings = detect_price_creep(txs)
    assert len(findings) == 1
    assert findings[0]["type"] == "subscription_creep"
    assert findings[0]["amount_cad"] == 2.0
    assert "March" in findings[0]["message"]


def test_forgotten_subscription_no_related_activity():
    today = date.today()
    txs = [
        _tx(
            id="g1",
            merchant="Adobe Creative Cloud",
            amount=-34.99,
            transaction_date=today - timedelta(days=90),
        ),
        _tx(
            id="g2",
            merchant="Adobe Creative Cloud",
            amount=-34.99,
            transaction_date=today - timedelta(days=60),
        ),
        _tx(
            id="g3",
            merchant="Adobe Creative Cloud",
            amount=-34.99,
            transaction_date=today - timedelta(days=30),
        ),
        # Unrelated spend — should not count as related activity
        _tx(
            id="g4",
            merchant="Loblaws",
            amount=-80.0,
            transaction_date=today - timedelta(days=10),
        ),
    ]
    findings = detect_forgotten_subscriptions(txs)
    assert any(f["evidence"]["merchant_key"] == "adobe creative cloud" for f in findings)


# ── Drafts ────────────────────────────────────────────────────────────────────


def test_draft_templates_fill_from_evidence():
    cancel = build_draft(
        "forgotten_subscription",
        {"merchant": "Adobe", "amount": 34.99, "last_date": "2026-04-01", "transaction_ids": ["a"]},
        user_name="Arsalan",
        account_email="a@example.com",
    )
    assert cancel["kind"] == "cancellation"
    assert "Adobe" in cancel["body"]
    assert "34.99" in cancel["body"]

    dispute = build_draft(
        "duplicate",
        {
            "merchant": "Best Buy",
            "amount": 199.99,
            "dates": ["2026-04-10", "2026-04-11"],
            "transaction_ids": ["d1", "d2"],
            "hours_apart": 24,
        },
    )
    assert dispute["kind"] == "dispute"
    assert "duplicate" in dispute["body"].lower()

    fee = build_draft(
        "fee",
        {
            "fee_type": "nsf",
            "amount": 45.0,
            "date": "2026-02-01",
            "description": "NSF FEE",
            "transaction_id": "f1",
        },
        institution="RBC",
    )
    assert fee["kind"] == "fee_reversal"
    assert "NSF" in fee["body"]


# ── Service + API ─────────────────────────────────────────────────────────────


def _seed_user_with_leaks(db_session):
    user = User(id="leak-user", email="leaks@test.com", name="Leak Tester")
    account = Account(
        id="leak-acc",
        user_id=user.id,
        name="Chequing",
        institution="RBC",
        account_type="checking",
    )
    db_session.add_all([user, account])

    # Planted FX markup
    db_session.add(
        Transaction(
            id="plant-fx",
            account_id=account.id,
            transaction_date=date(2026, 6, 1),
            description="AMAZON.COM USD 100.00",
            amount=-145.0,
            category="Shopping",
            merchant="Amazon",
        )
    )
    # Planted duplicate
    d0 = date(2026, 5, 1)
    db_session.add(
        Transaction(
            id="plant-dup-a",
            account_id=account.id,
            transaction_date=d0,
            description="BEST BUY #1234",
            amount=-199.99,
            category="Shopping",
            merchant="Best Buy",
        )
    )
    db_session.add(
        Transaction(
            id="plant-dup-b",
            account_id=account.id,
            transaction_date=d0 + timedelta(days=1),
            description="BEST BUY #1234",
            amount=-199.99,
            category="Shopping",
            merchant="Best Buy",
        )
    )
    # Planted NSF fee
    db_session.add(
        Transaction(
            id="plant-fee",
            account_id=account.id,
            transaction_date=date(2026, 3, 12),
            description="NSF FEE",
            amount=-45.0,
            category="Bank Fees",
            merchant="RBC",
        )
    )
    # Planted price creep
    for i, amt in enumerate([9.99, 9.99, 12.99, 12.99]):
        db_session.add(
            Transaction(
                id=f"plant-creep-{i}",
                account_id=account.id,
                transaction_date=date(2026, 1 + i, 8),
                description="SPOTIFY PREMIUM",
                amount=-amt,
                category="Subscriptions",
                merchant="Spotify",
            )
        )
    # Benign grocery — should not create a leak
    db_session.add(
        Transaction(
            id="plant-benign",
            account_id=account.id,
            transaction_date=date(2026, 6, 10),
            description="LOBLAWS #5521",
            amount=-67.43,
            category="Groceries",
            merchant="Loblaws",
        )
    )
    db_session.commit()
    return user


def test_scan_all_leaks_precision(db_session):
    user = _seed_user_with_leaks(db_session)
    findings = scan_all_leaks(db_session, user.id)
    types = {f["type"] for f in findings}

    assert "fx_markup" in types
    assert "duplicate" in types
    assert "fee" in types
    assert "subscription_creep" in types

    # Precision: every finding amount should be > 0 (except unverifiable)
    positive = [f for f in findings if not (f.get("evidence") or {}).get("unverifiable")]
    assert all(float(f["amount_cad"]) > 0 for f in positive)

    # Benign grocery must not appear as duplicate/fee/fx
    for f in findings:
        ev = f.get("evidence") or {}
        desc = str(ev.get("description") or "")
        merchant = str(ev.get("merchant") or "")
        assert "Loblaws" not in merchant or f["type"] in (
            "forgotten_subscription",
        )  # groceries aren't forgotten subs
        assert "LOBLAWS" not in desc.upper() or f["type"] != "fee"


def test_upsert_preserves_dismissed(db_session):
    user = _seed_user_with_leaks(db_session)
    findings = scan_all_leaks(db_session, user.id)
    rows = upsert_findings(db_session, user.id, findings)
    assert rows
    target = rows[0]
    target.status = "dismissed"
    db_session.commit()

    again = scan_all_leaks(db_session, user.id)
    upsert_findings(db_session, user.id, again)
    refreshed = db_session.get(LeakFinding, target.id)
    assert refreshed is not None
    assert refreshed.status == "dismissed"


def test_leaks_api_endpoints(client, db_session):
    user = _seed_user_with_leaks(db_session)

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        listed = client.get("/leaks/")
        assert listed.status_code == 200
        body = listed.json()
        assert len(body) >= 3
        leak_id = body[0]["id"]

        patched = client.patch(f"/leaks/{leak_id}", json={"status": "resolved"})
        assert patched.status_code == 200
        assert patched.json()["status"] == "resolved"

        # Find a fee or duplicate for draft
        fee_or_dup = next(
            (x for x in body if x["type"] in ("fee", "duplicate", "forgotten_subscription")),
            body[0],
        )
        draft = client.post(f"/leaks/{fee_or_dup['id']}/draft", json={})
        assert draft.status_code == 200
        assert "body" in draft.json()
        assert draft.json()["subject"]

        summary = client.get("/leaks/summary")
        assert summary.status_code == 200
        assert "total_found_cad" in summary.json()
    finally:
        app.dependency_overrides.pop(get_current_user, None)
