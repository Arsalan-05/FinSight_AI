"""Encrypt Plaid access tokens at rest (optional — requires PLAID_TOKEN_ENCRYPTION_KEY)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from db.models import BankConnection

_PREFIX = "enc:"


def _fernet() -> Fernet | None:
    raw = settings.plaid_token_encryption_key.strip()
    if not raw:
        return None
    try:
        return Fernet(raw.encode() if isinstance(raw, str) else raw)
    except Exception:
        digest = hashlib.sha256(raw.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
        return Fernet(key)


def encrypt_token(token: str) -> str:
    f = _fernet()
    if not f or not token:
        return token
    return _PREFIX + f.encrypt(token.encode()).decode()


def decrypt_token(stored: str) -> str:
    if not stored.startswith(_PREFIX):
        return stored
    f = _fernet()
    if not f:
        raise RuntimeError("Encrypted Plaid token but PLAID_TOKEN_ENCRYPTION_KEY is not set")
    try:
        return f.decrypt(stored[len(_PREFIX) :].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Failed to decrypt Plaid access token") from exc


def connection_access_token(connection: BankConnection) -> str:
    """Return plaintext access token for a BankConnection row."""
    return decrypt_token(connection.access_token)
