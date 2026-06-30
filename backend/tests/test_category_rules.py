"""Category rules CRUD and application."""

from datetime import date

from app.category_rules import add_rule, apply_rules_to_user_transactions, resolve_category
from db.models import Account, Transaction, User


def test_category_rules_crud_and_apply(client, db_session):
    user = User(id="rules-user", email="rules@test.com", name="Rules User")
    account = Account(
        id="acc-rules",
        user_id=user.id,
        name="Chequing",
        institution="RBC",
        account_type="checking",
    )
    tx = Transaction(
        id="tx-rules",
        account_id=account.id,
        transaction_date=date.today(),
        description="TIM HORTONS #1234",
        amount=-5.5,
        category="Uncategorized",
        merchant="Tim Hortons",
    )
    db_session.add_all([user, account, tx])
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    created = client.post(
        "/transactions/rules",
        json={"value": "tim hortons", "category": "Dining"},
    )
    assert created.status_code == 201

    listed = client.get("/transactions/rules")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    applied = client.post("/transactions/rules/apply")
    assert applied.status_code == 200
    assert applied.json()["updated"] == 1

    db_session.refresh(tx)
    assert tx.category == "Dining"

    app.dependency_overrides.pop(get_current_user, None)


def test_resolve_category_default():
    user = User(id="u1", email="u1@t.com", name="U1", category_rules_json="[]")
    cat = resolve_category(user, description="Coffee", merchant="Starbucks", default="Other")
    assert cat == "Other"


def test_add_rule_module(db_session):
    user = User(id="u2", email="u2@t.com", name="U2")
    db_session.add(user)
    db_session.commit()
    rule = add_rule(db_session, user, match="merchant_contains", value="Uber", category="Transport")
    assert rule["category"] == "Transport"
    assert apply_rules_to_user_transactions(db_session, user) == 0
