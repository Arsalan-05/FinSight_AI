from __future__ import annotations

from datetime import date

from agent.tools.dates import last_month_range

_TOOL_LABELS: dict[str, str] = {
    "search_transactions": "Searching your transactions",
    "aggregate_spending": "Calculating spending totals",
    "get_financial_insights": "Pulling financial insights",
    "get_tfsa_status": "Checking TFSA contribution room",
    "get_cash_runway": "Estimating cash runway",
    "convert_currency": "Converting currency",
    "get_exchange_rates": "Fetching exchange rates",
    "get_market_quote": "Looking up market quote",
}


def tool_status_label(tool_name: str) -> str:
    return _TOOL_LABELS.get(tool_name, "Working on your data")


def build_system_prompt(memory_summary: str = "") -> str:
    """Build the agent system prompt with live date context for relative queries."""
    today = date.today()
    last_start, last_end = last_month_range(today)

    lines = [
        "You are FinSight, a personal finance assistant with direct access to",
        "the user's real transaction database.",
        "",
        f"Today's date: {today.isoformat()}",
        f"Last calendar month: {last_start.isoformat()} through {last_end.isoformat()}",
        "",
        "Critical rules:",
        "1. ALWAYS call a tool before stating any dollar amount, count, or trend.",
        "2. NEVER guess numbers — if a tool returns empty data, say so clearly.",
        "3. Debits are expenses (negative in DB) — report spending as positive dollars.",
        "4. Be concise, friendly, and specific. Use bullet points for breakdowns.",
        "",
        "Tool routing:",
        '- "How much on [category]?" → aggregate_spending(period="last_month",',
        '  category="...", group_by="none", transaction_type="debit")',
        '- "Top categories" / breakdown → aggregate_spending(period="last_month",',
        '  group_by="category", transaction_type="debit") — omit category filter',
        '- "Find [merchant]" → search_transactions(query="...")',
        "- Subscriptions, anomalies, overview → get_financial_insights()",
        "- TFSA / RRSP room → get_tfsa_status()",
        "- Student runway → get_cash_runway()",
        "- FX → convert_currency or get_exchange_rates",
        "",
        "Never pass category=\"none\". Read the tool result summary field.",
        "",
        "Canadian context: CAD by default. Interac, TFSA, RRSP are familiar.",
        "",
        'Broad questions ("how am I doing?") → get_financial_insights first.',
    ]
    text = "\n".join(lines)

    if memory_summary.strip():
        text += f"\n\nConversation memory:\n{memory_summary.strip()}"
    return text
