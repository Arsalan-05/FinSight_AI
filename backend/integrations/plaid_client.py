"""Plaid REST client — compliant bank linking (US + Canada)."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

_PLAID_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


def plaid_configured() -> bool:
    return bool(settings.plaid_client_id and settings.plaid_secret)


def _base_url() -> str:
    return _PLAID_HOSTS.get(settings.plaid_env, _PLAID_HOSTS["sandbox"])


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    if not plaid_configured():
        raise RuntimeError("Plaid is not configured")
    payload = {
        "client_id": settings.plaid_client_id,
        "secret": settings.plaid_secret,
        **body,
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{_base_url()}{path}", json=payload)
        if response.is_error:
            detail = response.text
            raise RuntimeError(f"Plaid API error {response.status_code}: {detail}")
        return response.json()


def create_link_token(*, user_id: str) -> dict[str, Any]:
    return _post(
        "/link/token/create",
        {
            "user": {"client_user_id": user_id},
            "client_name": "FinSight AI",
            "products": ["transactions"],
            "country_codes": ["CA", "US"],
            "language": "en",
            "transactions": {"days_requested": 730},
        },
    )


def exchange_public_token(public_token: str) -> dict[str, Any]:
    return _post("/item/public_token/exchange", {"public_token": public_token})


def get_accounts(access_token: str) -> dict[str, Any]:
    return _post("/accounts/get", {"access_token": access_token})


def sync_transactions(access_token: str, cursor: str = "") -> dict[str, Any]:
    body: dict[str, Any] = {"access_token": access_token}
    if cursor:
        body["cursor"] = cursor
    return _post("/transactions/sync", body)


def get_item(access_token: str) -> dict[str, Any]:
    return _post("/item/get", {"access_token": access_token})


def remove_item(access_token: str) -> dict[str, Any]:
    return _post("/item/remove", {"access_token": access_token})
