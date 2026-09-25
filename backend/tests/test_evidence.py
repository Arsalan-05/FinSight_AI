"""Tests for evidence tagging helpers."""

from __future__ import annotations

from agent.guardrails.evidence import (
    EvidenceStore,
    attach_evidence_ids_to_tool_result,
    format_money,
    parse_evidence_tags,
)
from agent.routing import route_model


def test_evidence_store_registers_sequential_ids() -> None:
    store = EvidenceStore()
    a = store.register("aggregate_spending", {"period": "last_month"}, {"total": -100.0})
    b = store.register("calculate", {"expression": "1+1"}, {"result": 2})
    assert a == "ev_1"
    assert b == "ev_2"
    items = store.list()
    assert len(items) == 2
    assert items[0]["tool"] == "aggregate_spending"
    assert store.get("ev_2")["result"]["result"] == 2


def test_format_money() -> None:
    assert format_money(412.3, "ev_1") == "[[$412.30|ev_1]]"
    assert format_money(0, "ev_9") == "[[$0.00|ev_9]]"


def test_parse_evidence_tags() -> None:
    text = "Dining [[$412.30|ev_1]] and transit [[$88.00|ev_2]]."
    tags = parse_evidence_tags(text)
    assert len(tags) == 2
    assert tags[0]["amount"] == 412.30
    assert tags[0]["evidence_id"] == "ev_1"
    assert tags[1]["evidence_id"] == "ev_2"
    assert tags[0]["raw"].startswith("[[$")


def test_attach_evidence_ids_to_tool_result() -> None:
    result = {"total": -50.0, "count": 2}
    attached = attach_evidence_ids_to_tool_result(result, "ev_3")
    assert attached["evidence_id"] == "ev_3"
    assert "evidence_id" not in result
    assert attached["total"] == -50.0


def test_route_model_heuristic() -> None:
    assert route_model("How much did I spend on coffee?") == "8b"
    assert route_model("What if I max my TFSA this year?") == "70b"
    assert route_model("Compare RRSP vs TFSA for me") == "70b"
    assert route_model("Help me plan a savings schedule") == "70b"
