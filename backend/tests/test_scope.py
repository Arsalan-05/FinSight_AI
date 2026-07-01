"""Finance-only scope guard."""

from agent.scope import finance_scope_refusal


def test_refuses_celebrity_trivia() -> None:
    assert finance_scope_refusal("Who is Salman Khan?") is not None


def test_refuses_entertainment_keywords() -> None:
    assert finance_scope_refusal("Tell me about the latest Bollywood movie") is not None


def test_allows_finance_questions() -> None:
    assert finance_scope_refusal("How much did I spend on dining last month?") is None
    assert finance_scope_refusal("What is my TFSA room?") is None
    assert finance_scope_refusal("Help me with this spend alert") is None


def test_allows_finance_education() -> None:
    assert finance_scope_refusal("What is the difference between credit and debit?") is None


def test_general_trivia_without_finance_signal() -> None:
    assert finance_scope_refusal("Who is the president of France?") is not None
