"""Tests for the LangGraph agent: graph loop, tools, and session persistence."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, PropertyMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import build_graph
from agent.memory import load_messages, load_session, save_session
from agent.runner import run_agent
from agent.tools import execute_tool
from app.config import settings
from db.models import Account, Transaction, User


def _seed_account(db_session) -> str:
    user = User(email="agent@test.com", name="Agent User")
    db_session.add(user)
    db_session.flush()
    account = Account(
        user_id=user.id,
        name="Checking",
        institution="Chase",
        account_type="checking",
    )
    db_session.add(account)
    db_session.flush()
    db_session.add(
        Transaction(
            account_id=account.id,
            transaction_date=date(2026, 5, 1),
            description="Coffee",
            amount=-5.50,
            category="Dining",
            merchant="Starbucks",
        )
    )
    db_session.commit()
    return account.id


class TestExecuteTool:
    def test_aggregate_spending_tool(self, db_session) -> None:
        _seed_account(db_session)
        result = json.loads(
            execute_tool(
                "aggregate_spending",
                {"group_by": "category", "transaction_type": "debit"},
                db=db_session,
            )
        )
        assert result["groups"][0]["category"] == "Dining"
        assert result["groups"][0]["total"] == -5.50

    def test_search_when_embeddings_unconfigured(self, db_session) -> None:
        with patch.object(
            type(settings),
            "embeddings_configured",
            new_callable=PropertyMock,
            return_value=False,
        ):
            result = json.loads(
                execute_tool(
                    "search_transactions",
                    {"query": "coffee"},
                    db=db_session,
                )
            )
        assert "error" in result


class TestSessionPersistence:
    def test_load_creates_new_session(self, db_session) -> None:
        session = load_session(db_session, "new-session-1")
        assert session.id == "new-session-1"
        assert session.messages_json == "[]"
        assert session.memory_summary == ""

    def test_save_and_load_messages(self, db_session) -> None:
        messages = [HumanMessage(content="Hello"), AIMessage(content="Hi there")]
        save_session(db_session, "sess-1", messages, "User greeted.")
        loaded = load_messages(load_session(db_session, "sess-1"))
        assert len(loaded) == 2
        assert loaded[0].content == "Hello"
        assert loaded[1].content == "Hi there"

        session = load_session(db_session, "sess-1")
        assert session.memory_summary == "User greeted."


class TestAgentGraph:
    @patch("agent.graph.call_llm")
    def test_react_loop_calls_tools_then_responds(self, mock_llm: MagicMock, db_session) -> None:
        _seed_account(db_session)
        mock_llm.side_effect = [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tc1",
                        "name": "aggregate_spending",
                        "args": {"group_by": "category", "transaction_type": "debit"},
                    }
                ],
            ),
            AIMessage(content="You spent $5.50 on Dining."),
        ]

        graph = build_graph(db_session)
        result = graph.invoke(
            {
                "messages": [HumanMessage(content="How much did I spend on dining?")],
                "memory_summary": "",
                "session_id": "test-graph",
            }
        )

        assert mock_llm.call_count == 2
        final = result["messages"][-1]
        assert isinstance(final, AIMessage)
        assert "5.50" in str(final.content)

    @patch("agent.graph.call_llm")
    def test_direct_response_without_tools(self, mock_llm: MagicMock, db_session) -> None:
        mock_llm.return_value = AIMessage(content="Hello! How can I help with your finances?")

        graph = build_graph(db_session)
        result = graph.invoke(
            {
                "messages": [HumanMessage(content="Hi")],
                "memory_summary": "",
                "session_id": "test-direct",
            }
        )

        assert mock_llm.call_count == 1
        assert "finances" in str(result["messages"][-1].content).lower()


class TestRunAgent:
    @patch("agent.runner.summarize_memory")
    @patch("agent.graph.call_llm")
    def test_run_agent_persists_session(
        self,
        mock_llm: MagicMock,
        mock_summarize: MagicMock,
        db_session,
    ) -> None:
        _seed_account(db_session)
        mock_llm.side_effect = [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "tc1",
                        "name": "aggregate_spending",
                        "args": {"group_by": "none", "transaction_type": "debit"},
                    }
                ],
            ),
            AIMessage(content="Total spending: $5.50."),
        ]
        mock_summarize.return_value = "User asked about total spending."

        result = run_agent(
            "What's my total spending?",
            "persist-session",
            db_session,
            update_memory=True,
        )

        assert "5.50" in result.reply
        session = load_session(db_session, "persist-session")
        assert session.memory_summary == "User asked about total spending."
        messages = load_messages(session)
        assert len(messages) >= 3

    @patch("agent.runner.summarize_memory")
    @patch("agent.graph.call_llm")
    def test_multi_turn_memory_loads_prior_messages(
        self,
        mock_llm: MagicMock,
        mock_summarize: MagicMock,
        db_session,
    ) -> None:
        mock_llm.return_value = AIMessage(content="Sure, I can help with that.")
        mock_summarize.return_value = "Prior context."

        run_agent("First question", "multi-turn", db_session)
        run_agent("Follow-up question", "multi-turn", db_session)

        assert mock_llm.call_count == 2
        second_call_messages = mock_llm.call_args_list[1][0][0]
        assert len(second_call_messages) >= 3
