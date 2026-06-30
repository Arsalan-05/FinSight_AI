"""User data export and account deletion."""

from datetime import date

from db.models import Account, Budget, ChatSession, Transaction, User


def _seed_user(db_session):
    user = User(id="export-user", email="export@test.com", name="Export User")
    account = Account(
        id="acc-export",
        user_id=user.id,
        name="Chequing",
        institution="TD",
        account_type="checking",
    )
    tx = Transaction(
        id="tx-export",
        account_id=account.id,
        transaction_date=date(2026, 6, 1),
        description="Coffee",
        amount=-5.0,
        category="Dining",
    )
    budget = Budget(id="bud-export", user_id=user.id, category="Dining", monthly_limit=50)
    session = ChatSession(id="chat-export", user_id=user.id, title="Test", messages_json="[]")
    db_session.add_all([user, account, tx, budget, session])
    db_session.commit()
    return user


def test_export_user_data(client, db_session):
    user = _seed_user(db_session)

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    r = client.get("/auth/me/export")
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == "export@test.com"
    assert len(data["accounts"]) == 1
    assert len(data["transactions"]) == 1
    assert len(data["budgets"]) == 1
    assert len(data["chat_sessions"]) == 1

    app.dependency_overrides.pop(get_current_user, None)


def test_delete_user_cascades(client, db_session):
    user = _seed_user(db_session)

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    r = client.delete("/auth/me")
    assert r.status_code == 204

    assert db_session.get(User, user.id) is None
    assert db_session.query(Account).count() == 0
    assert db_session.query(Transaction).count() == 0
    assert db_session.query(Budget).count() == 0
    assert db_session.query(ChatSession).count() == 0

    app.dependency_overrides.pop(get_current_user, None)
