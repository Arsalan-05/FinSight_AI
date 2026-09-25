"""Tests for GET /dashboard single-payload Overview endpoint."""

from __future__ import annotations

from datetime import date, timedelta


def test_dashboard_empty(client) -> None:
    r = client.get("/dashboard/")
    assert r.status_code == 200
    body = r.json()
    assert body["accounts"] == []
    assert body["recent"] == []
    assert body["kpis"]["cur_spend"] == 0
    assert body["daily"] == []
    assert body["insight_cards"] == []


def test_dashboard_aggregates(client, db_session) -> None:
    user = client.post("/users/", json={"email": "dash@example.com", "name": "Dash"}).json()
    account = client.post(
        "/accounts/",
        json={
            "user_id": user["id"],
            "name": "Chequing",
            "institution": "TD",
            "account_type": "checking",
        },
    ).json()

    today = date.today()
    # current month debit + credit
    client.post(
        "/transactions/",
        json={
            "account_id": account["id"],
            "transaction_date": today.isoformat(),
            "description": "Groceries",
            "amount": -40.0,
            "category": "Groceries",
            "merchant": "Loblaws",
        },
    )
    client.post(
        "/transactions/",
        json={
            "account_id": account["id"],
            "transaction_date": today.isoformat(),
            "description": "Pay",
            "amount": 100.0,
            "category": "Income",
            "merchant": "Employer",
        },
    )
    # last month debit
    last_month = (today.replace(day=1) - timedelta(days=1))
    client.post(
        "/transactions/",
        json={
            "account_id": account["id"],
            "transaction_date": last_month.isoformat(),
            "description": "Rent",
            "amount": -50.0,
            "category": "Housing",
            "merchant": "Landlord",
        },
    )

    r = client.get("/dashboard/")
    assert r.status_code == 200
    body = r.json()
    assert len(body["accounts"]) == 1
    assert body["kpis"]["cur_spend"] == 40.0
    assert body["kpis"]["cur_income"] == 100.0
    assert body["kpis"]["prev_spend"] == 50.0
    assert body["kpis"]["credit_count"] == 1
    assert body["kpis"]["net_savings"] == 60.0
    assert any(c["category"] == "Groceries" for c in body["top_categories"])
    assert len(body["recent"]) >= 1
    assert isinstance(body["daily"], list)
