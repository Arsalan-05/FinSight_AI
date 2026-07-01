"""CLI entry point for testing the LangGraph agent without the API layer.

Usage:
    uv run python -m agent.cli "How much did I spend on dining?"
    uv run python -m agent.cli --session my-session "What about last month?"

Requires Groq (free, same as Render) + Voyage (free search, same as Render):
    GROQ_API_KEY=...   # console.groq.com
    VOYAGE_API_KEY=... # dash.voyageai.com (200M free tokens)
"""

from __future__ import annotations

import argparse
import sys
import uuid

import agent._warn  # noqa: F401 — must run before httpx/langgraph imports
from agent.llm import ollama_llm_available
from agent.runner import run_agent
from app.config import settings
from db.base import SessionLocal
from rag.embedder import embeddings_runtime_available, ollama_embeddings_available


def _check_setup() -> None:
    provider = settings.effective_llm_provider
    if provider == "groq" and not settings.groq_api_key:
        print("Error: GROQ_API_KEY is required for chat.", file=sys.stderr)
        print("Free key: https://console.groq.com", file=sys.stderr)
        sys.exit(1)
    if provider == "anthropic" and not settings.anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic.", file=sys.stderr)
        sys.exit(1)
    if provider == "ollama" and not ollama_llm_available():
        print(
            f"Error: Ollama is not running or {settings.ollama_model} is not installed.",
            file=sys.stderr,
        )
        print("Prefer Groq (free): set GROQ_API_KEY and LLM_PROVIDER=groq", file=sys.stderr)
        sys.exit(1)

    if settings.effective_embedding_provider == "ollama" and not ollama_embeddings_available():
        print("Warning: nomic-embed-text not found — semantic search disabled.", file=sys.stderr)
        print(
            "Prefer Voyage (free): set VOYAGE_API_KEY from https://dash.voyageai.com",
            file=sys.stderr,
        )
    elif settings.effective_embedding_provider == "voyage" and not embeddings_runtime_available():
        print("Warning: VOYAGE_API_KEY not set — semantic search disabled.", file=sys.stderr)
        print("Free key: https://dash.voyageai.com (voyage-4-large, 200M tokens)", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="FinSight AI agent CLI")
    parser.add_argument("message", help="User message to send to the agent")
    parser.add_argument(
        "--session",
        default=None,
        help="Session ID for conversation memory (default: random UUID)",
    )
    args = parser.parse_args()

    _check_setup()

    session_id = args.session or str(uuid.uuid4())
    db = SessionLocal()
    try:
        reply = run_agent(args.message, session_id, db)
        print(reply)
        print(f"\n[session: {session_id}]", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    main()
