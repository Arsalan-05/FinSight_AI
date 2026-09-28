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


def test_rounded_restatement_is_grounded() -> None:
    tools = [json.dumps({"amount": -186.40, "total": 4952.59})]
    result = verify_numeric_grounding("That $186 dinner pushed you to ~$4,950.", tools)
    assert result.ok


def test_period_conversion_and_ratio_are_grounded() -> None:
    tools = [json.dumps({"monthly": 54.99, "saved": 450.0, "target": 1599.0})]
    answer = "GoodLife costs $659.88 a year, and you're 28.1% of the way to the iPhone."
    result = verify_numeric_grounding(answer, tools)
    assert result.ok, result.unverified


def test_prose_sources_ground_goal_amounts() -> None:
    goals = "Goals: iPhone 17 Pro — saved 450.00 of 1599.00, due 2026-12-15"
    result = verify_numeric_grounding("You've saved $450 of $1,599.", [goals])
    assert result.ok


def test_table_total_of_shown_rows_is_grounded() -> None:
    tools = [json.dumps({"groups": [313.21, 115.42, 49.09, 27.86, 22.59]})]
    answer = (
        "| Dining | [[$313.21|ev_1]] |\n| Shopping | [[$115.42|ev_1]] |\n"
        "| Groceries | [[$49.09|ev_1]] |\n| Transport | [[$27.86|ev_1]] |\n"
        "| Subscriptions | [[$22.59|ev_1]] |\n| **Total** | **$528.17** |"
    )
    result = verify_numeric_grounding(answer, tools)
    assert result.ok, result.unverified


def test_total_of_unshown_amounts_is_not_grounded() -> None:
    tools = [json.dumps({"groups": [313.21, 115.42, 49.09, 27.86, 22.59]})]
    result = verify_numeric_grounding("All in, you spent $528.17.", tools)
    assert not result.ok


def test_strip_does_not_mangle_longer_amounts_or_tags() -> None:
    answer = "Miku was [[$186.40|ev_2]] — about $186.40 — versus $186 claimed."
    stripped = strip_unverified(answer, [("$186", 186.0)])
    assert "[[$186.40|ev_2]]" in stripped
    assert "about $186.40" in stripped
    assert "versus [unverified] claimed" in stripped


def test_strip_unverified_appends_notice() -> None:
    answer = "You spent $999.99 somehow."
    stripped = strip_unverified(answer, [("$999.99", 999.99)])
    assert "$999.99" not in stripped
    assert "[unverified]" in stripped
    assert "could not be verified" in stripped
