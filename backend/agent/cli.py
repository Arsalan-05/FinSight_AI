"""CLI entry point for testing the LangGraph agent without the API layer.

Usage:
    uv run python -m agent.cli "How much did I spend on dining?"
    uv run python -m agent.cli --session my-session "What about last month?"

Requires Ollama (free) by default:
    ollama pull llama3.2
    ollama pull nomic-embed-text
"""

from __future__ import annotations

import agent._warn  # noqa: F401 — must run before httpx/langgraph imports

import argparse
import sys
import uuid

from agent.llm import ollama_llm_available
from agent.runner import run_agent
from app.config import settings
from db.base import SessionLocal
from rag.embedder import ollama_embeddings_available


def _check_setup() -> None:
    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic.", file=sys.stderr)
        sys.exit(1)

    if settings.llm_provider == "ollama" and not ollama_llm_available():
        print("Error: Ollama is not running or llama3.2 is not installed.", file=sys.stderr)
        print(file=sys.stderr)
        print("Free setup (no API keys):", file=sys.stderr)
        print("  1. Install Ollama: https://ollama.com", file=sys.stderr)
        print("  2. ollama pull llama3.2", file=sys.stderr)
        print("  3. ollama pull nomic-embed-text", file=sys.stderr)
        sys.exit(1)

    if settings.embedding_provider == "ollama" and not ollama_embeddings_available():
        print("Warning: nomic-embed-text not found — semantic search may fail.", file=sys.stderr)
        print("Run: ollama pull nomic-embed-text", file=sys.stderr)


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
