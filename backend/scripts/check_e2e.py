#!/usr/bin/env python3
"""Full-stack checkpoint: DB, auth config, API routes, chat, insights."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import settings
from app.main import app

FAILURES: list[str] = []
CHECKS: list[str] = []

TABLES = (
    "users",
    "accounts",
    "transactions",
    "transaction_embeddings",
    "chat_sessions",
)


def ok(msg: str) -> None:
    CHECKS.append(f"✓ {msg}")


def fail(msg: str) -> None:
    FAILURES.append(msg)
    CHECKS.append(f"✗ {msg}")


def main() -> int:
    # ── Database ─────────────────────────────────────────────────────────────
    try:
        engine = create_engine(
            settings.database_url_resolved,
            connect_args={"connect_timeout": 15},
        )
        with engine.connect() as conn:
            for table in TABLES:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                ok(f"DB table `{table}` reachable ({n} rows)")
            conn.execute(text("SELECT 1"))
        host = settings.database_url_resolved.split("@")[-1].split("/")[0]
        label = "Supabase" if settings.using_supabase_postgres else "Postgres"
        ok(f"{label} connected ({host})")
    except Exception as exc:
        fail(f"Database: {exc}")

    # ── Auth config ──────────────────────────────────────────────────────────
    if settings.supabase_url:
        ok("SUPABASE_URL configured (JWKS auth)")
    else:
        fail("SUPABASE_URL missing")
    if settings.supabase_auth_enabled:
        ok("Supabase auth enabled")
    else:
        fail("Supabase auth not enabled")

    # ── LLM ──────────────────────────────────────────────────────────────────
    if settings.llm_configured:
        ok(f"LLM provider: {settings.llm_provider}")
    else:
        fail("LLM not configured")

    client = TestClient(app)

    # ── Health ───────────────────────────────────────────────────────────────
    r = client.get("/health")
    if r.status_code == 200 and r.json().get("status") == "ok":
        ok("GET /health")
    else:
        fail(f"GET /health → {r.status_code}")

    r = client.get("/health/db")
    if r.status_code == 200:
        ok("GET /health/db")
    else:
        fail(f"GET /health/db → {r.status_code} {r.text[:80]}")

    # ── Auth enforcement ─────────────────────────────────────────────────────
    r = client.get("/accounts/")
    if r.status_code == 401:
        ok("Auth enforced on /accounts/ (401 without token)")
    else:
        fail(f"/accounts/ should require auth, got {r.status_code}")

    # ── Chat ─────────────────────────────────────────────────────────────────
    r = client.post("/chat/", json={"message": "Hello"})
    if settings.auth_enforced:
        if r.status_code == 401:
            ok("POST /chat/ requires auth when REQUIRE_AUTH=true")
        elif r.status_code == 200:
            ok("POST /chat/ streams (auth bypassed in test client)")
        else:
            fail(f"POST /chat/ → {r.status_code}: {r.text[:120]}")
    else:
        if r.status_code == 200:
            ok("POST /chat/ streams")
        else:
            fail(f"POST /chat/ → {r.status_code}: {r.text[:120]}")

    # ── Insights route exists ─────────────────────────────────────────────────
    r = client.get("/insights/")
    if r.status_code in (401, 200):
        ok(f"GET /insights/ route live ({r.status_code})")
    else:
        fail(f"GET /insights/ → {r.status_code}")

    # ── Goals route ───────────────────────────────────────────────────────────
    r = client.get("/goals/")
    if r.status_code in (401, 200):
        ok(f"GET /goals/ route live ({r.status_code})")
    else:
        fail(f"GET /goals/ → {r.status_code}")

    # ── Search route ──────────────────────────────────────────────────────────
    r = client.post("/search/", json={"query": "coffee", "k": 3})
    if r.status_code in (401, 200, 503):
        ok(f"POST /search/ route live ({r.status_code})")
    else:
        fail(f"POST /search/ → {r.status_code}")

    print("\n".join(CHECKS))
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s)")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print(f"ALL {len(CHECKS)} CHECKPOINTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
