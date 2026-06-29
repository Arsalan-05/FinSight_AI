"""Tests for proactive insights engine."""

from __future__ import annotations

from datetime import date

from db.models import Transaction
from insights.recurring import detect_recurring_charges
from insights.tfsa import tfsa_contribution_status


def _seed_txs(db_session, account_id: str):
    for i in range(3):
        db_session.add(
            Transaction(
                account_id=account_id,
                transaction_date=date(2026, 2 + i, 12),
                description="Spotify Premium",
                amount=-11.99,
                category="Subscriptions",
                merchant="Spotify",
            )
        )
    db_session.add(
        Transaction(
            account_id=account_id,
            transaction_date=date(2026, 4, 1),
            description="TFSA Contribution",
            amount=500.0,
            category="Savings",
            merchant="RBC TFSA",
        )
    )
    db_session.commit()


def _make_account(client, user_id: str):
    return client.post(
        "/accounts/",
        json={
            "user_id": user_id,
            "name": "RBC",
            "institution": "RBC",
            "account_type": "checking",
        },
    ).json()


def test_recurring_detects_spotify(client, db_session):
    user = client.post("/users/", json={"email": "ins@example.com", "name": "Ins"}).json()
    account = _make_account(client, user["id"])
    _seed_txs(db_session, account["id"])

    recurring = detect_recurring_charges(db_session, account_ids=[account["id"]])
    assert any("Spotify" in r["merchant"] for r in recurring)


def test_insights_endpoint(client, db_session):
    user = client.post("/users/", json={"email": "ins2@example.com", "name": "Ins2"}).json()
    account = _make_account(client, user["id"])
    _seed_txs(db_session, account["id"])

    r = client.get("/insights/")
    assert r.status_code == 200
    body = r.json()
    assert "insight_cards" in body
    assert "subscriptions" in body


def test_tfsa_status(db_session, client):
    user = client.post("/users/", json={"email": "tfsa@example.com", "name": "Tfsa"}).json()
    account = _make_account(client, user["id"])
    _seed_txs(db_session, account["id"])

    status = tfsa_contribution_status(db_session, account_ids=[account["id"]])
    assert status["year"] == 2026
    assert "tfsa" in status
