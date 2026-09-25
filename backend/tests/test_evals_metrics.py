"""Unit tests for eval metrics helpers (no LLM)."""

from __future__ import annotations

import json

from evals.metrics import (
    extract_currency_amounts,
    hallucinated_number_rate,
    mrr,
    ndcg_at_k,
    numeric_match,
    recall_at_k,
    refusal_accuracy,
    tool_selection_accuracy,
)


class TestNumericMatch:
    def test_exact(self) -> None:
        assert numeric_match(12.34, 12.34) is True

    def test_within_tolerance(self) -> None:
        assert numeric_match(100.005, 100.0, tolerance=0.01) is True

    def test_outside_tolerance(self) -> None:
        assert numeric_match(100.05, 100.0, tolerance=0.01) is False

    def test_string_currency(self) -> None:
        assert numeric_match("$1,450.00", 1450.0) is True

    def test_none_rejected(self) -> None:
        assert numeric_match(None, 10) is False
        assert numeric_match(10, None) is False


class TestToolSelectionAccuracy:
    def test_exact_match(self) -> None:
        result = tool_selection_accuracy(
            ["aggregate_spending"],
            ["aggregate_spending"],
        )
        assert result["exact"] is True
        assert result["partial"] == 1.0

    def test_partial_overlap(self) -> None:
        result = tool_selection_accuracy(
            ["aggregate_spending", "search_transactions"],
            ["aggregate_spending"],
        )
        assert result["exact"] is False
        assert 0.0 < result["partial"] < 1.0

    def test_both_empty(self) -> None:
        result = tool_selection_accuracy([], [])
        assert result["exact"] is True
        assert result["partial"] == 1.0

    def test_no_overlap(self) -> None:
        result = tool_selection_accuracy(["search_web"], ["aggregate_spending"])
        assert result["exact"] is False
        assert result["partial"] == 0.0


class TestHallucinatedNumberRate:
    def test_grounded_amount(self) -> None:
        tool = [json.dumps({"total": -1450.0, "amount": 1450.0})]
        result = hallucinated_number_rate("Rent is $1450.00", tool)
        assert result["rate"] == 0.0
        assert result["hallucinated"] == []

    def test_hallucinated_amount(self) -> None:
        tool = [json.dumps({"total": 10.0})]
        result = hallucinated_number_rate("You spent $9,999.00 somehow", tool)
        assert result["rate"] == 1.0
        assert 9999.0 in result["hallucinated"]

    def test_empty_answer(self) -> None:
        result = hallucinated_number_rate("", ['{"total": 1}'])
        assert result["rate"] == 0.0

    def test_extract_currency_helper(self) -> None:
        amounts = extract_currency_amounts("Paid CAD 48.00 and $3.50 ATM fee")
        assert 48.0 in amounts
        assert 3.5 in amounts


class TestRetrievalMetrics:
    def test_recall_at_k(self) -> None:
        relevant = ["a", "b", "c"]
        ranked = ["x", "a", "y", "b", "z"]
        assert recall_at_k(relevant, ranked, k=5) == 2 / 3

    def test_recall_empty_relevant(self) -> None:
        assert recall_at_k([], ["a"], k=5) == 0.0

    def test_mrr_first_hit(self) -> None:
        assert mrr(["a"], ["a", "b"]) == 1.0

    def test_mrr_second_hit(self) -> None:
        assert mrr(["b"], ["a", "b"]) == 0.5

    def test_mrr_miss(self) -> None:
        assert mrr(["z"], ["a", "b"]) == 0.0

    def test_ndcg_perfect(self) -> None:
        relevant = ["a", "b"]
        ranked = ["a", "b", "c"]
        assert ndcg_at_k(relevant, ranked, k=2) == 1.0

    def test_ndcg_partial(self) -> None:
        relevant = ["a", "b"]
        ranked = ["x", "a", "b"]
        score = ndcg_at_k(relevant, ranked, k=3)
        assert 0.0 < score < 1.0


class TestRefusalAccuracy:
    def test_correct_refuse(self) -> None:
        assert refusal_accuracy(should_refuse=True, did_refuse=True) is True

    def test_false_positive(self) -> None:
        assert refusal_accuracy(should_refuse=False, did_refuse=True) is False

    def test_missed_refuse(self) -> None:
        assert refusal_accuracy(should_refuse=True, did_refuse=False) is False
