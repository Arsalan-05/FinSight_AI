-- Run once in the Supabase SQL editor before Alembic migrations.
-- Required for semantic search embeddings.

CREATE EXTENSION IF NOT EXISTS vector;
