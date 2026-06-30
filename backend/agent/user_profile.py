"""Per-user financial intelligence — learned from transaction history and conversations."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Transaction, User

_EMPTY_PROFILE: dict[str, Any] = {
    "learned_summary": "",
    "preferences": [],
    "risk_flags": [],
    "updated_at": None,
}


def load_agent_profile(user: User) -> dict[str, Any]:
    try:
        data = json.loads(user.agent_profile_json or "{}")
        return data if isinstance(data, dict) else dict(_EMPTY_PROFILE)
    except json.JSONDecodeError:
        return dict(_EMPTY_PROFILE)


def save_agent_profile(db: Session, user: User, profile: dict[str, Any]) -> dict[str, Any]:
    user.agent_profile_json = json.dumps(profile)
    db.commit()
    db.refresh(user)
    return profile


def build_data_profile(
    db: Session,
    *,
    account_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Factual spending fingerprint from the user's real transactions (no LLM)."""
    q = db.query(Transaction)
    if account_ids is not None:
        if not account_ids:
            return {"transaction_count": 0, "message": "No accounts linked yet."}
        q = q.filter(Transaction.account_id.in_(account_ids))

    total = q.count()
    if total == 0:
        return {"transaction_count": 0, "message": "No transactions ingested yet."}

    today = date.today()
    window_start = today - timedelta(days=90)

    base = q.filter(Transaction.transaction_date >= window_start)
    debits = base.filter(Transaction.amount < 0)
    credits = base.filter(Transaction.amount > 0)

    spend_total = float(debits.with_entities(func.sum(Transaction.amount)).scalar() or 0)
    income_total = float(credits.with_entities(func.sum(Transaction.amount)).scalar() or 0)

    top_categories = (
        debits.with_entities(
            Transaction.category,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount))
        .limit(6)
        .all()
    )

    top_merchants = (
        debits.filter(Transaction.merchant.isnot(None))
        .with_entities(
            Transaction.merchant,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .group_by(Transaction.merchant)
        .order_by(func.sum(Transaction.amount))
        .limit(6)
        .all()
    )

    largest = (
        debits.order_by(Transaction.amount.asc()).limit(5).all()
    )

    months_active = max(
        1,
        (today - window_start).days / 30.0,
    )
    avg_monthly_spend = abs(spend_total) / months_active
    avg_monthly_income = income_total / months_active

    return {
        "transaction_count": total,
        "window_days": 90,
        "avg_monthly_spend_cad": round(avg_monthly_spend, 2),
        "avg_monthly_income_cad": round(avg_monthly_income, 2),
        "net_monthly_cad": round(avg_monthly_income + spend_total / months_active, 2),
        "top_categories": [
            {
                "category": row.category,
                "total_spend_cad": round(abs(float(row.total)), 2),
                "transactions": int(row.cnt),
            }
            for row in top_categories
        ],
        "top_merchants": [
            {
                "merchant": row.merchant,
                "total_spend_cad": round(abs(float(row.total)), 2),
                "transactions": int(row.cnt),
            }
            for row in top_merchants
            if row.merchant
        ],
        "largest_recent_expenses": [
            {
                "date": tx.transaction_date.isoformat(),
                "description": tx.description,
                "amount_cad": float(tx.amount),
                "category": tx.category,
            }
            for tx in largest
        ],
    }


def profile_narrative(data_profile: dict[str, Any], learned: dict[str, Any]) -> str:
    """Human-readable block injected into the agent system prompt."""
    lines: list[str] = ["## Your learned understanding of this user"]

    if data_profile.get("transaction_count", 0) == 0:
        lines.append("No transaction history yet — guide them to upload CSV or add accounts.")
        return "\n".join(lines)

    lines.append(
        f"Based on {data_profile['transaction_count']} transactions "
        f"(last {data_profile.get('window_days', 90)} days analyzed):"
    )
    lines.append(
        f"- Avg monthly spend: ${data_profile.get('avg_monthly_spend_cad', 0):,.2f} CAD"
    )
    lines.append(
        f"- Avg monthly income: ${data_profile.get('avg_monthly_income_cad', 0):,.2f} CAD"
    )
    if data_profile.get("top_categories"):
        cats = ", ".join(
            f"{c['category']} (${c['total_spend_cad']:,.0f})"
            for c in data_profile["top_categories"][:4]
        )
        lines.append(f"- Top spend categories: {cats}")

    learned_summary = learned.get("learned_summary", "").strip()
    if learned_summary:
        lines.append(f"\nLearned from past conversations:\n{learned_summary}")

    prefs = learned.get("preferences") or []
    if prefs:
        lines.append("User preferences: " + "; ".join(str(p) for p in prefs[:6]))

    flags = learned.get("risk_flags") or []
    if flags:
        lines.append("Watch areas: " + "; ".join(str(f) for f in flags[:4]))

    lines.append(
        "\nUse this profile to personalize advice. "
        "Still verify numbers with tools before stating amounts."
    )
    return "\n".join(lines)


def update_learned_profile(
    messages: list[BaseMessage],
    current: dict[str, Any],
    data_profile: dict[str, Any],
) -> dict[str, Any]:
    """Update persistent user learnings from the conversation (not model fine-tuning)."""
    recent: list[str] = []
    for msg in messages[-8:]:
        if isinstance(msg, HumanMessage):
            recent.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            recent.append(f"Assistant: {msg.content}")
    if not recent:
        return current

    data_hint = json.dumps(
        {
            "avg_monthly_spend": data_profile.get("avg_monthly_spend_cad"),
            "top_categories": [
                c.get("category") for c in data_profile.get("top_categories", [])[:3]
            ],
        },
        default=str,
    )

    prompt = (
        "You maintain a persistent user financial profile for a personal finance app. "
        "Update the JSON fields based on the recent exchange and spending fingerprint. "
        "Keep learned_summary under 120 words. "
        "preferences and risk_flags are short strings (max 6 each). "
        "Do not invent dollar amounts not in the data.\n\n"
        f"Current profile JSON:\n{json.dumps(current, default=str)}\n\n"
        f"Spending fingerprint:\n{data_hint}\n\n"
        f"Recent exchange:\n" + "\n".join(recent) + "\n\n"
        "Reply with ONLY valid JSON: "
        '{"learned_summary":"...","preferences":["..."],"risk_flags":["..."]}'
    )

    try:
        from agent.llm import call_llm

        response = call_llm([HumanMessage(content=prompt)], "")
        raw = str(response.content or "")
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            if isinstance(parsed, dict):
                merged = dict(current)
                merged.update(
                    {
                        "learned_summary": str(parsed.get("learned_summary", ""))[:800],
                        "preferences": (parsed.get("preferences") or [])[:8],
                        "risk_flags": (parsed.get("risk_flags") or [])[:6],
                        "updated_at": date.today().isoformat(),
                    }
                )
                return merged
    except (json.JSONDecodeError, ValueError, RuntimeError):
        pass
    return current
