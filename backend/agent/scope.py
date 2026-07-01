"""Finance-only scope guard — reject obvious off-topic questions before the agent runs."""

from __future__ import annotations

import re

_FINANCE_RE = re.compile(
    r"\b("
    r"spend|spending|spent|budget|budgets|transaction|transactions|money|saving|savings|"
    r"tfsa|rrsp|fhsa|resp|invest|investing|investment|portfolio|rent|mortgage|loan|debt|"
    r"credit|debit|subscription|subscriptions|account|accounts|bank|banking|"
    r"income|salary|paycheque|paycheck|pay|expense|expenses|cash|runway|"
    r"grocer|dining|merchant|category|categories|alert|alerts|goal|goals|"
    r"finance|financial|cad|dollar|dollars|tax|taxes|cra|etf|etfs|stock|stocks|"
    r"market|markets|rate|rates|interest|inflation|dividend|crypto|"
    r"afford|affordable|net\s*worth|balance|balances|transfer|interac|"
    r"weekly\s*brief|overspend|frugal|emergency\s*fund"
    r")\b",
    re.I,
)

_OFF_TOPIC_RE = re.compile(
    r"\b("
    r"actor|actress|celebrity|celebrities|cricketer|footballer|soccer|nba|nfl|"
    r"singer|rapper|movie|movies|film|films|bollywood|hollywood|"
    r"recipe|recipes|cooking|weather|horoscope|joke|jokes|"
    r"homework|essay|math\s*problem|physics|chemistry|"
    r"video\s*game|fortnite|minecraft"
    r")\b",
    re.I,
)

_GENERAL_TRIVIA_RE = re.compile(
    r"^(?:who is|who's|who was|what is|what's|tell me about|where is|where's)\s+.+",
    re.I,
)


def finance_scope_refusal(message: str) -> str | None:
    """
    Return a short refusal if the message is clearly outside personal finance.

    Saves LLM tokens by skipping the agent for obvious trivia / entertainment asks.
    When unsure, returns None and the system prompt handles soft boundaries.
    """
    text = (message or "").strip()
    if not text:
        return None

    if _FINANCE_RE.search(text):
        return None

    if _OFF_TOPIC_RE.search(text):
        return _REFUSAL

    if _GENERAL_TRIVIA_RE.match(text) and len(text.split()) <= 12:
        return _REFUSAL

    return None


_REFUSAL = (
    "I'm FinSight — your personal finance advisor. I can help with spending, budgets, "
    "savings, TFSA/RRSP, subscriptions, and questions grounded in your transaction data. "
    "I can't answer general trivia or entertainment questions here. "
    "Try asking something like: “How much did I spend on dining last month?”"
)
