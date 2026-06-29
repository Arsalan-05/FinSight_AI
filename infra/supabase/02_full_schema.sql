-- FinSight AI — full schema for Supabase SQL Editor
-- Run AFTER 01_extensions.sql in: Dashboard → SQL → New query
-- Project: https://supabase.com/dashboard/project/zibzsxwceivnziplciuq/sql

CREATE EXTENSION IF NOT EXISTS vector;

-- Alembic version tracking
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

-- users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    auth_id VARCHAR(36) UNIQUE,
    goals_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_auth_id ON users (auth_id);

-- accounts
CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    institution VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_accounts_user_id ON accounts (user_id);

-- transactions
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL REFERENCES accounts(id),
    transaction_date DATE NOT NULL,
    description VARCHAR(500) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'Uncategorized',
    merchant VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_transactions_account_id ON transactions (account_id);
CREATE INDEX IF NOT EXISTS ix_transactions_transaction_date ON transactions (transaction_date);
CREATE INDEX IF NOT EXISTS ix_transactions_category ON transactions (category);

-- chat_sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    title VARCHAR(255) NOT NULL DEFAULT '',
    messages_json TEXT NOT NULL DEFAULT '[]',
    memory_summary TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id ON chat_sessions (user_id);

-- transaction_embeddings (768-dim for Ollama nomic-embed-text)
CREATE TABLE IF NOT EXISTS transaction_embeddings (
    id VARCHAR(36) PRIMARY KEY,
    transaction_id VARCHAR(36) NOT NULL UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_transaction_embeddings_transaction_id
    ON transaction_embeddings (transaction_id);

DROP INDEX IF EXISTS idx_tx_embeddings_ivfflat;
CREATE INDEX IF NOT EXISTS idx_tx_embeddings_hnsw
    ON transaction_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Mark migrations as applied (Alembic head)
INSERT INTO alembic_version (version_num)
VALUES ('g7b8c9d0e1f2')
ON CONFLICT (version_num) DO NOTHING;
