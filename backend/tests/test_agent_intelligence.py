"""Tests for web search and user financial profile."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage

from agent.tools.web_search import search_web
from agent.user_profile import build_data_profile, profile_narrative, update_learned_profile
from db.models import Account, Transaction, User


def _seed(db_session) -> tuple[User, list[str]]:
    user = User(email="profile@test.com", name="Profile User")
    db_session.add(user)
    db_session.flush()
    acct = Account(
        user_id=user.id,
        name="Chequing",
        institution="TD",
        account_type="checking",
    )
    db_session.add(acct)
    db_session.flush()
    db_session.add(
        Transaction(
            account_id=acct.id,
            transaction_date=date(2026, 5, 15),
            description="Groceries",
            amount=-85.00,
            category="Groceries",
            merchant="Loblaws",
        )
    )
    db_session.commit()
    return user, [acct.id]


class TestWebSearch:
    @patch("agent.tools.web_search._search_tavily")
    def test_search_web_tavily(self, mock_tavily: object) -> None:
        mock_tavily.return_value = [  # type: ignore[attr-defined]
            {"title": "TFSA 2026", "snippet": "Limit is $7000", "url": "https://example.com"}
        ]
        result = search_web("TFSA limit Canada 2026")
        assert result["provider"] == "tavily"
        assert result["count"] >= 1

    @patch("agent.tools.web_search._search_tavily", return_value=None)
    @patch("agent.tools.web_search._search_duckduckgo")
    def test_search_web_ddg_fallback(self, mock_ddg: object, _tavily: object) -> None:
        mock_ddg.return_value = [  # type: ignore[attr-defined]
            {"title": "Result", "snippet": "snippet", "url": "https://x.com"}
        ]
        result = search_web("student budget tips")
        assert result["provider"] == "duckduckgo"


class TestUserProfile:
    def test_build_data_profile(self, db_session) -> None:
        _, account_ids = _seed(db_session)
        profile = build_data_profile(db_session, account_ids=account_ids)
        assert profile["transaction_count"] == 1
        assert profile["top_categories"][0]["category"] == "Groceries"

    def test_profile_narrative(self, db_session) -> None:
        _, account_ids = _seed(db_session)
        data = build_data_profile(db_session, account_ids=account_ids)
        text = profile_narrative(data, {"learned_summary": "User is cost-conscious."})
        assert "Groceries" in text
        assert "cost-conscious" in text

    @patch("agent.llm.call_llm")
    def test_update_learned_profile(self, mock_llm: object) -> None:
        mock_llm.return_value = AIMessage(  # type: ignore[attr-defined]
            content=(
                '{"learned_summary":"Wants to cut dining.",'
                '"preferences":["budget meals"],"risk_flags":["dining"]}'
            )
        )
        updated = update_learned_profile(
            [HumanMessage(content="How do I spend less on food?")],
            {"learned_summary": "", "preferences": [], "risk_flags": []},
            {"avg_monthly_spend_cad": 500, "top_categories": [{"category": "Dining"}]},
        )
        assert "dining" in updated["learned_summary"].lower() or updated["risk_flags"]
