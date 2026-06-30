"""Tests for Plaid bank integration."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from app.config import settings
from db.models import Account, BankConnection, Transaction, User
from integrations.plaid_sync import sync_connection


def test_plaid_status_disabled(client) -> None:
    with patch.object(settings, "plaid_client_id", ""):
        with patch.object(settings, "plaid_secret", ""):
            r = client.get("/integrations/plaid/status")
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_plaid_status_enabled(client) -> None:
    with patch.object(settings, "plaid_client_id", "test-id"):
        with patch.object(settings, "plaid_secret", "test-secret"):
            with patch.object(settings, "plaid_env", "sandbox"):
                r = client.get("/integrations/plaid/status")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    assert data["environment"] == "sandbox"


def test_link_token_requires_auth_or_plaid(client) -> None:
    with patch.object(settings, "plaid_client_id", ""):
        r = client.post("/integrations/plaid/link-token")
    assert r.status_code in (401, 503)


def test_plaid_sync_modified_and_removed(db_session, monkeypatch):
    user = User(id="plaid-u", email="p@test.com", name="Plaid")
    conn = BankConnection(
        id="conn-1",
        user_id=user.id,
        item_id="item-1",
        access_token="enc:token",
        institution_name="Test Bank",
        status="active",
    )
    account = Account(
        id="acc-plaid",
        user_id=user.id,
        name="Chequing",
        institution="Test Bank",
        account_type="checking",
        plaid_account_id="pa-1",
        bank_connection_id=conn.id,
    )
    existing = Transaction(
        id="tx-existing",
        account_id=account.id,
        transaction_date=date.today(),
        description="Old name",
        amount=-10.0,
        category="Uncategorized",
        plaid_transaction_id="ptx-1",
    )
    removed = Transaction(
        id="tx-remove",
        account_id=account.id,
        transaction_date=date.today(),
        description="Gone",
        amount=-5.0,
        category="Uncategorized",
        plaid_transaction_id="ptx-2",
    )
    db_session.add_all([user, conn, account, existing, removed])
    db_session.commit()

    monkeypatch.setattr(
        "integrations.plaid_sync.connection_access_token",
        lambda _c: "access-token",
    )
    monkeypatch.setattr(
        "integrations.plaid_sync.get_accounts",
        lambda _t: {
            "accounts": [
                {
                    "account_id": "pa-1",
                    "name": "Chequing",
                    "type": "depository",
                    "subtype": "checking",
                }
            ]
        },
    )
    monkeypatch.setattr(
        "integrations.plaid_sync.sync_transactions",
        lambda _t, _c: {
            "added": [],
            "modified": [
                {
                    "transaction_id": "ptx-1",
                    "account_id": "pa-1",
                    "date": date.today().isoformat(),
                    "name": "Updated merchant",
                    "amount": 12.0,
                    "merchant_name": "Shop",
                }
            ],
            "removed": [{"transaction_id": "ptx-2"}],
            "has_more": False,
            "next_cursor": "cursor-2",
        },
    )
    monkeypatch.setattr("integrations.plaid_sync._embed_transactions", lambda *_a, **_k: None)
    monkeypatch.setattr("notifications.alerts.check_budget_alerts", lambda *_a, **_k: [])

    result = sync_connection(db_session, conn)
    assert result["modified"] == 1
    assert result["removed"] == 1

    db_session.refresh(existing)
    assert existing.description == "Updated merchant"
    assert db_session.get(Transaction, removed.id) is None
