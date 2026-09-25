"""Tests for numeric grounding guardrail."""

from __future__ import annotations

import json

from agent.guardrails.numeric import (
    amounts_from_tool_outputs,
    extract_amounts,
    strip_unverified,
    verify_numeric_grounding,
)


def test_extract_currency_and_percent() -> None:
    text = "You spent $1,234.56 on dining (12.5% of total) and CAD 88.00 on transit."
    amounts = extract_amounts(text)
    values = [v for _, v in amounts]
    assert 1234.56 in values
    assert 12.5 in values
    assert 88.0 in values


def test_extract_evidence_tag_amount() -> None:
    amounts = extract_amounts("Dining was [[$412.30|ev_1]] last month.")
    assert len(amounts) == 1
    assert amounts[0][1] == 412.30
    assert "ev_1" in amounts[0][0]


def test_amounts_from_tool_outputs_rounds() -> None:
    payload = json.dumps({"total": -412.301, "groups": [{"total": 88.5}]})
    known = amounts_from_tool_outputs([payload])
    assert 412.30 in known
    assert 88.5 in known


def test_verify_ok_when_grounded() -> None:
    tools = [json.dumps({"total": -412.30, "count": 3})]
    answer = "You spent [[$412.30|ev_1]] on dining."
    result = verify_numeric_grounding(answer, tools)
    assert result.ok
    assert len(result.verified) == 1
    assert result.unverified == []


def test_verify_allows_sum_and_diff() -> None:
    tools = [json.dumps({"a": 100.0, "b": 40.0})]
    answer = "Combined that is $140.00, and the gap is $60.00."
    result = verify_numeric_grounding(answer, tools)
    assert result.ok
    assert len(result.verified) == 2


def test_verify_fails_on_hallucinated_amount() -> None:
    tools = [json.dumps({"total": -50.0})]
    answer = "You spent $999.99 on coffee."
    result = verify_numeric_grounding(answer, tools)
    assert not result.ok
    assert any(abs(v - 999.99) < 0.001 for _, v in result.unverified)


def test_strip_unverified_appends_notice() -> None:
    answer = "You spent $999.99 somehow."
    stripped = strip_unverified(answer, [("$999.99", 999.99)])
    assert "$999.99" not in stripped
    assert "[unverified]" in stripped
    assert "could not be verified" in stripped
