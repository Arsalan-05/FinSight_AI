# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FinSight AI is a full-stack personal finance intelligence agent. It ingests personal transaction data, builds a RAG knowledge base over it using pgvector, and exposes a chat interface where a stateful LangGraph agent answers questions, identifies spending patterns, and provides recommendations. The LLM layer runs on the Anthropic Claude API. External tools are connected via MCP. The full system runs in Docker and deploys to Railway.

## Repo layout

```
backend/        FastAPI app, LangGraph agent, RAG pipeline, MCP tool integrations
frontend/       Next.js chat UI
infra/          Docker Compose, Railway config, DB migration scripts
```

## Dev environment

All services run via Docker Compose. The canonical way to start the full stack locally:

```bash
docker compose up --build
```

For backend-only development without Docker:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

For frontend-only development:

```bash
cd frontend
npm install
npm run dev
```

## Backend commands

```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/path/to/test_file.py

# Run a single test by name
uv run pytest tests/path/to/test_file.py::test_function_name

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy app/
```

## Frontend commands

```bash
npm run build        # production build
npm run lint         # ESLint
npm run type-check   # tsc --noEmit
```

## Architecture

### Four layers

**1. Data + vector store (`backend/db/`)**
PostgreSQL with the pgvector extension. Two main concerns: relational tables for raw transaction data (user, account, transaction), and a `transaction_embeddings` table that stores vector representations for RAG retrieval. Migrations managed by Alembic.

**2. RAG pipeline (`backend/rag/`)**
On ingest, transactions are chunked, embedded via the Claude API (or a dedicated embeddings model), and written to pgvector. At query time, the agent retrieves the top-k semantically relevant transactions and injects them into the prompt as context. The retriever is a standalone module the agent calls as a tool.

**3. LangGraph agent (`backend/agent/`)**
A stateful ReAct-style agent graph. State carries conversation history and a memory summary that persists across turns. Tool nodes include: the RAG retriever, a spending-analysis tool (aggregates over the DB), and MCP-connected external tools (e.g. currency conversion, market data). The graph compiles to a runnable that the FastAPI route invokes per chat message.

**4. API + MCP (`backend/app/`, `backend/mcp/`)**
FastAPI serves the chat endpoint (`POST /chat`) and transaction ingestion endpoints. MCP tool servers are defined in `backend/mcp/` and registered on the LangGraph agent at startup. The frontend communicates only with FastAPI — it has no direct DB or agent access.

### Key data flow

```
User message → FastAPI /chat
  → LangGraph agent (loads session state from DB)
    → RAG retriever (pgvector similarity search)
    → Tool calls (MCP servers, spending aggregator)
    → Claude API (claude-sonnet-4-6 or claude-opus-4-7)
  → Response streamed back to Next.js UI
```

### Claude API usage

Use `claude-sonnet-4-6` as the default model for agent inference. Use prompt caching (`cache_control`) on the system prompt and retrieved RAG context — these are stable across turns and benefit most from caching. Reserve `claude-opus-4-7` for heavier offline tasks (e.g. batch insight generation). The Anthropic SDK is the only client — do not use LangChain's Anthropic wrapper.

### Environment variables

The backend reads all secrets from environment variables (never hardcoded). Key vars:

```
ANTHROPIC_API_KEY
DATABASE_URL          # postgres://user:pass@host:5432/finsight
PGVECTOR_COLLECTION   # name of the embeddings table/collection
```

## Conventions

- Python package manager: `uv`. Do not use pip directly.
- All backend Python code lives under `backend/app/` (application code) or `backend/` subdirectories (agent, rag, mcp, db).
- FastAPI dependency injection is used for DB sessions and agent instances — do not instantiate these inside route handlers.
- LangGraph state is typed with a `TypedDict`. New state fields must be added there, not passed ad-hoc.
- MCP tool definitions live in `backend/mcp/` with one file per tool server.
