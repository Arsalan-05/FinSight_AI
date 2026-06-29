# Run once in Supabase SQL Editor (Dashboard → SQL) before Alembic migrations.
# Required for semantic search / RAG embeddings.

CREATE EXTENSION IF NOT EXISTS vector;
