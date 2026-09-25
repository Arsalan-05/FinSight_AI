"""Deterministic seeded demo persona for evals."""

from __future__ import annotations

from typing import Any

__all__ = ["build_fixture_transactions", "load_fixture_into_db"]


def build_fixture_transactions(*args: Any, **kwargs: Any):
    from evals.fixtures.seed_persona import build_fixture_transactions as _build

    return _build(*args, **kwargs)


def load_fixture_into_db(*args: Any, **kwargs: Any):
    from evals.fixtures.load import load_fixture_into_db as _load

    return _load(*args, **kwargs)
