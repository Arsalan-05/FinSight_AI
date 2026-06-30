"""Bootstrap endpoint tests."""

from __future__ import annotations

from app.auth import get_current_user
from app.main import app
from db.models import User


def test_bootstrap_provisions_data(client, db_session) -> None:
    user = User(email="boot@test.com", name="Boot User")
    db_session.add(user)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.post("/auth/bootstrap")
        assert r.status_code == 200
        data = r.json()
        assert data["account_count"] >= 2
        assert data["transaction_count"] > 0
        assert data["provisioned_demo"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)
