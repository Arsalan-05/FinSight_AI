"""Tests for Plaid bank integration."""

from __future__ import annotations

from unittest.mock import patch

from app.config import settings


def test_plaid_status_disabled(client) -> None:
    with patch.object(settings, "plaid_client_id", ""):
        with patch.object(settings, "plaid_secret", ""):
            r = client.get("/integrations/plaid/status")
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_plaid_status_enabled(client) -> None:
    with patch.object(settings, "plaid_client_id", "test-id"):
        with patch.object(settings, "plaid_secret", "test-secret"):
            with patch.object(settings, "plaid_env", "sandbox"):
                r = client.get("/integrations/plaid/status")
    assert r.status_code == 200
    data = r.json()
    assert data["enabled"] is True
    assert data["environment"] == "sandbox"


def test_link_token_requires_auth_or_plaid(client) -> None:
    with patch.object(settings, "plaid_client_id", ""):
        r = client.post("/integrations/plaid/link-token")
    assert r.status_code in (401, 503)
