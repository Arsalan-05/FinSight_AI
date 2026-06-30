"""User-defined transaction categorization rules."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from db.models import Account, Transaction, User


def load_rules(user: User) -> list[dict[str, Any]]:
    try:
        data = json.loads(user.category_rules_json or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_rules(db: Session, user: User, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    user.category_rules_json = json.dumps(rules)
    db.commit()
    db.refresh(user)
    return rules


def add_rule(
    db: Session,
    user: User,
    *,
    match: str,
    value: str,
    category: str,
) -> dict[str, Any]:
    if match != "merchant_contains":
        raise ValueError("Unsupported match type")
    rules = load_rules(user)
    rule = {
        "id": str(uuid.uuid4()),
        "match": match,
        "value": value.strip(),
        "category": category.strip(),
    }
    rules.append(rule)
    save_rules(db, user, rules)
    return rule


def delete_rule(db: Session, user: User, rule_id: str) -> bool:
    rules = load_rules(user)
    new_rules = [r for r in rules if r.get("id") != rule_id]
    if len(new_rules) == len(rules):
        return False
    save_rules(db, user, new_rules)
    return True


def resolve_category(
    user: User,
    *,
    description: str,
    merchant: str | None,
    default: str,
) -> str:
    """Return category from first matching rule, else default."""
    haystack = f"{merchant or ''} {description}".lower()
    for rule in load_rules(user):
        if rule.get("match") != "merchant_contains":
            continue
        needle = str(rule.get("value", "")).lower().strip()
        if needle and needle in haystack:
            return str(rule.get("category", default))
    return default


def apply_rules_to_user_transactions(db: Session, user: User) -> int:
    """Re-apply all rules to the user's transactions. Returns rows updated."""
    rules = load_rules(user)
    if not rules:
        return 0
    account_ids = [a.id for a in db.query(Account.id).filter(Account.user_id == user.id).all()]
    if not account_ids:
        return 0
    txs = db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).all()
    updated = 0
    for tx in txs:
        new_cat = resolve_category(
            user,
            description=tx.description,
            merchant=tx.merchant,
            default=tx.category,
        )
        if new_cat != tx.category:
            tx.category = new_cat
            updated += 1
    if updated:
        db.commit()
    return updated
