"""Budget CRUD and spend tracking."""

from datetime import date

from db.models import Account, Budget, Transaction, User


def test_create_and_list_budget(client, db_session):
    user = User(id="budget-user", email="budget@test.com", name="Budget User")
    db_session.add(user)
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    r = client.post("/budgets/", json={"category": "Dining", "monthly_limit": 200})
    assert r.status_code == 201
    budget_id = r.json()["id"]

    listed = client.get("/budgets/")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["category"] == "Dining"
    assert float(items[0]["monthly_limit"]) == 200
    assert items[0]["spent_this_month"] == 0

    client.delete(f"/budgets/{budget_id}")
    assert client.get("/budgets/").json() == []

    app.dependency_overrides.pop(get_current_user, None)


def test_budget_spend_calculation(client, db_session, monkeypatch):
    user = User(id="spend-user", email="spend@test.com", name="Spend User")
    account = Account(
        id="acc-1",
        user_id=user.id,
        name="Chequing",
        institution="RBC",
        account_type="checking",
    )
    db_session.add_all([user, account])
    today = date.today().isoformat()
    db_session.add(
        Transaction(
            id="tx-1",
            account_id=account.id,
            transaction_date=date.today(),
            description="Lunch",
            amount=-45.0,
            category="Dining",
        )
    )
    db_session.add(
        Budget(id="bud-1", user_id=user.id, category="Dining", monthly_limit=100)
    )
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    items = client.get("/budgets/").json()
    assert items[0]["spent_this_month"] == 45.0
    assert items[0]["percent_used"] == 45.0

    app.dependency_overrides.pop(get_current_user, None)
