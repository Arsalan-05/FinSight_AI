"""Notification preferences, budget alerts, and digest."""

import json
from datetime import date

from db.models import Account, Budget, Notification, Transaction, User
from notifications.alerts import check_budget_alerts


def test_budget_alert_creates_notification(db_session):
    user = User(id="notif-user", email="n@test.com", name="N User")
    account = Account(
        id="acc-n",
        user_id=user.id,
        name="Card",
        institution="RBC",
        account_type="credit",
    )
    db_session.add_all([user, account])
    db_session.add(
        Budget(id="bud-n", user_id=user.id, category="Dining", monthly_limit=50)
    )
    db_session.add(
        Transaction(
            id="tx-n",
            account_id=account.id,
            transaction_date=date.today(),
            description="Lunch",
            amount=-60.0,
            category="Dining",
        )
    )
    db_session.commit()

    created = check_budget_alerts(db_session, user)
    assert len(created) == 1
    assert "Dining" in created[0].title


def test_budget_alerts_respect_prefs(db_session):
    user = User(
        id="notif-user2",
        email="n2@test.com",
        name="N2",
        alert_prefs_json=json.dumps({"spend_alerts": False}),
    )
    account = Account(
        id="acc-n2",
        user_id=user.id,
        name="Card",
        institution="RBC",
        account_type="credit",
    )
    db_session.add_all([user, account])
    db_session.add(
        Budget(id="bud-n2", user_id=user.id, category="Dining", monthly_limit=10)
    )
    db_session.add(
        Transaction(
            id="tx-n2",
            account_id=account.id,
            transaction_date=date.today(),
            description="Dinner",
            amount=-80.0,
            category="Dining",
        )
    )
    db_session.commit()

    assert check_budget_alerts(db_session, user) == []


def test_notification_preferences_api(client, db_session):
    user = User(id="pref-user", email="p@test.com", name="P User")
    db_session.add(user)
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    r = client.get("/notifications/preferences")
    assert r.status_code == 200
    assert r.json()["spend_alerts"] is True

    r2 = client.patch("/notifications/preferences", json={"email_digest": True})
    assert r2.status_code == 200
    assert r2.json()["email_digest"] is True

    app.dependency_overrides.pop(get_current_user, None)


def test_notifications_list(client, db_session):
    user = User(id="list-user", email="l@test.com", name="L User")
    note = Notification(
        id="note-1",
        user_id=user.id,
        kind="spend_alert",
        severity="warning",
        title="Test",
        body="Body",
    )
    db_session.add_all([user, note])
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    r = client.get("/notifications/")
    assert r.status_code == 200
    assert len(r.json()) == 1

    app.dependency_overrides.pop(get_current_user, None)


def test_agent_profile_api(client, db_session):
    user = User(
        id="prof-user",
        email="prof@test.com",
        name="Prof",
        agent_profile_json='{"learned_summary":"Likes TFSA tips","preferences":["save more"]}',
    )
    db_session.add(user)
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    r = client.get("/auth/me/profile")
    assert r.status_code == 200
    assert "TFSA" in r.json()["learned_summary"]

    r2 = client.delete("/auth/me/profile")
    assert r2.status_code == 204

    db_session.refresh(user)
    assert json.loads(user.agent_profile_json)["learned_summary"] == ""

    app.dependency_overrides.pop(get_current_user, None)
