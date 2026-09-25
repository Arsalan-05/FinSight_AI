"""Tests for the safe calculate tool."""

from __future__ import annotations

import json

from agent.tools import execute_tool
from agent.tools.calculate import calculate


def test_calculate_basic_ops() -> None:
    assert calculate("2 + 3 * 4")["result"] == 14
    assert calculate("(100 - 40) / 2")["result"] == 30
    assert calculate("-5 + 12.5")["result"] == 7.5


def test_calculate_money_expression() -> None:
    out = calculate("(412.30 + 88.50) * 0.13")
    assert "error" not in out
    assert abs(float(out["result"]) - 65.104) < 1e-9


def test_calculate_rejects_names_and_calls() -> None:
    assert "error" in calculate("__import__('os').system('id')")
    assert "error" in calculate("pow(2, 10)")
    assert "error" in calculate("1 ** 2")


def test_calculate_division_by_zero() -> None:
    assert calculate("1 / 0")["error"] == "Division by zero"


def test_calculate_empty() -> None:
    assert "error" in calculate("")
    assert "error" in calculate("   ")


def test_calculate_via_execute_tool(db_session) -> None:
    raw = execute_tool("calculate", {"expression": "10 + 5"}, db=db_session)
    data = json.loads(raw)
    assert data["result"] == 15
