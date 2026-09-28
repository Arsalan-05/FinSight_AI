"""Category rules CRUD and application."""

from datetime import date

from app.category_rules import (
    add_rule,
    apply_rules_to_user_transactions,
    load_rules,
    resolve_category,
)
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


def _seed_merchant_history(db_session):
    user = User(id="learn-user", email="learn@test.com", name="Learn User")
    account = Account(
        id="acc-learn",
        user_id=user.id,
        name="Chequing",
        institution="TD",
        account_type="checking",
    )
    txs = [
        Transaction(
            id=f"tx-learn-{i}",
            account_id=account.id,
            transaction_date=date(2026, 9, i + 1),
            description=f"COSTCO WHOLESALE #{i}",
            amount=-80.0,
            category="Shopping",
            merchant="Costco",
        )
        for i in range(3)
    ]
    other = Transaction(
        id="tx-learn-other",
        account_id=account.id,
        transaction_date=date(2026, 9, 5),
        description="SHOPPERS DRUG MART",
        amount=-12.0,
        category="Shopping",
        merchant="Shoppers Drug Mart",
    )
    db_session.add_all([user, account, *txs, other])
    db_session.commit()
    return user, txs, other


def _as_user(user):
    from app.auth import get_current_user_optional
    from app.main import app

    app.dependency_overrides[get_current_user_optional] = lambda: user
    return lambda: app.dependency_overrides.pop(get_current_user_optional, None)


def test_category_edit_learns_merchant_rule(client, db_session):
    user, txs, other = _seed_merchant_history(db_session)
    restore = _as_user(user)
    try:
        res = client.patch(f"/transactions/{txs[0].id}", json={"category": "Groceries"})
        assert res.status_code == 200
        body = res.json()
        assert body["category"] == "Groceries"
        assert body["recategorized"] == 2

        for tx in txs:
            db_session.refresh(tx)
            assert tx.category == "Groceries"
        db_session.refresh(other)
        assert other.category == "Shopping"

        db_session.refresh(user)
        rules = load_rules(user)
        assert rules[0]["value"] == "costco"
        assert rules[0]["category"] == "Groceries"
        assert (
            resolve_category(user, description="COSTCO GAS", merchant="Costco", default="Transport")
            == "Groceries"
        )

        client.patch(f"/transactions/{txs[1].id}", json={"category": "Household"})
        db_session.refresh(user)
        costco_rules = [r for r in load_rules(user) if r["value"] == "costco"]
        assert len(costco_rules) == 1
        assert costco_rules[0]["category"] == "Household"
    finally:
        restore()


def test_category_edit_can_skip_learning(client, db_session):
    user, txs, _ = _seed_merchant_history(db_session)
    restore = _as_user(user)
    try:
        res = client.patch(f"/transactions/{txs[0].id}?learn=false", json={"category": "Gifts"})
        assert res.status_code == 200
        assert res.json()["recategorized"] == 0
        db_session.refresh(txs[1])
        assert txs[1].category == "Shopping"
        db_session.refresh(user)
        assert load_rules(user) == []
    finally:
        restore()


def test_notes_edit_does_not_create_rule(client, db_session):
    user, txs, _ = _seed_merchant_history(db_session)
    restore = _as_user(user)
    try:
        res = client.patch(f"/transactions/{txs[0].id}", json={"notes": "bulk run"})
        assert res.status_code == 200
        assert res.json()["recategorized"] == 0
        db_session.refresh(user)
        assert load_rules(user) == []
    finally:
        restore()


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
