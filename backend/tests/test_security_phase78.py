"""Audit log + evals listing + security headers."""

from __future__ import annotations

from db.models import AuditLog, User


def test_security_headers_on_health(client) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "default-src" in r.headers.get("Content-Security-Policy", "")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert "X-Request-ID" in r.headers


def test_evals_list(client) -> None:
    r = client.get("/evals/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Seeded results from Phase 6 harness should be present in repo
    assert len(data) >= 1
    assert "id" in data[0]
    assert "file" in data[0]


def test_evals_get_one(client) -> None:
    listing = client.get("/evals/").json()
    run_id = listing[0]["id"]
    r = client.get(f"/evals/{run_id}")
    assert r.status_code == 200
    assert r.json()["id"] == run_id


def test_audit_list_for_user(client, db_session) -> None:
    user = User(id="audit-user", email="audit@test.com", name="Audit User")
    db_session.add(user)
    db_session.add(
        AuditLog(
            id="aud-1",
            user_id=user.id,
            action="export",
            resource_type="user",
            resource_id=user.id,
            detail_json='{"source":"test"}',
        )
    )
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get("/audit/")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        assert rows[0]["action"] == "export"
        assert rows[0]["id"] == "aud-1"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_export_sanitizes_formula_description(client, db_session) -> None:
    from datetime import date

    from db.models import Account, Transaction

    user = User(id="csv-user", email="csv@test.com", name="CSV User")
    account = Account(
        id="acc-csv",
        user_id=user.id,
        name="Chequing",
        institution="TD",
        account_type="checking",
    )
    tx = Transaction(
        id="tx-csv",
        account_id=account.id,
        transaction_date=date(2026, 6, 1),
        description="=HYPERLINK(\"http://evil\")",
        amount=-5.0,
        category="Dining",
    )
    db_session.add_all([user, account, tx])
    db_session.commit()

    from app.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get("/auth/me/export")
        assert r.status_code == 200
        desc = r.json()["transactions"][0]["description"]
        assert desc.startswith("'=")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
