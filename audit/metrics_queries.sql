-- FinSight AI: read-only production metrics queries
-- ----------------------------------------------------------------------------
-- Paste into the Supabase SQL editor (or psql) against YOUR production database.
-- Every statement is a SELECT, and the whole file runs inside a READ ONLY
-- transaction that is rolled back at the end, so nothing can be written.
--
-- Schema source: backend/db/models.py (13 tables). Column names match v2.0.0.
--
-- IMPORTANT CAVEATS BEFORE YOU QUOTE ANY OF THESE NUMBERS
--  1. Demo data cloning. backend/app/demo_provision.py clones every transaction
--     of the demo user (demo@finsight.ai) into each new user's account on first
--     sign-in (called from POST /auth/bootstrap, app/routers/auth.py:44). So raw
--     transaction counts are mostly synthetic. Use query 5b/5c, not 5a.
--  2. No activity timestamp on users. There is no last_login / last_seen column,
--     so "active users" below is a proxy: users with a chat session updated, a
--     transaction created, or a Plaid sync in the window.
--  3. No request, latency or error logging in the database. The app does not
--     store HTTP requests, per-request latency or error counts anywhere in
--     Postgres (no such table; request_id middleware only tags log lines).
--     Requests/day, average/p95 latency and error rate are NOT queryable here.
--     Get them from Railway metrics instead (see RESUME_METRICS.md, section 6).
--  4. audit_log and eval_runs tables exist but no application code writes to
--     them (grep for "AuditLog(" / "EvalRun(" finds only the model classes), so
--     expect 0 rows.
--  5. Exclude yourself and test accounts. Edit the excluded_emails list in the
--     CTE of each query if you have personal or test logins.
-- ----------------------------------------------------------------------------

BEGIN TRANSACTION READ ONLY;

-- ============================================================================
-- 1. Total users (excluding the demo account)
-- Returns: one row, total_users.
-- ============================================================================
SELECT COUNT(*) AS total_users
FROM users
WHERE email NOT IN ('demo@finsight.ai');

-- ============================================================================
-- 2. Signups by month
-- Returns: one row per month with the number of users created that month.
-- users.created_at is server_default now(), so it is the signup moment.
-- ============================================================================
SELECT date_trunc('month', created_at)::date AS month,
       COUNT(*)                              AS signups
FROM users
WHERE email NOT IN ('demo@finsight.ai')
GROUP BY 1
ORDER BY 1;

-- ============================================================================
-- 3. Active users in the last 30 days (PROXY, see caveat 2)
-- Returns: one row with each activity signal and the de-duplicated total.
-- ============================================================================
WITH chat_active AS (
    SELECT DISTINCT user_id FROM chat_sessions
    WHERE user_id IS NOT NULL AND updated_at >= now() - interval '30 days'
),
upload_active AS (
    SELECT DISTINCT a.user_id
    FROM transactions t JOIN accounts a ON a.id = t.account_id
    WHERE t.created_at >= now() - interval '30 days'
),
plaid_active AS (
    SELECT DISTINCT user_id FROM bank_connections
    WHERE last_synced_at >= now() - interval '30 days'
),
all_active AS (
    SELECT user_id FROM chat_active
    UNION SELECT user_id FROM upload_active
    UNION SELECT user_id FROM plaid_active
)
SELECT
    (SELECT COUNT(*) FROM chat_active)   AS users_who_chatted_30d,
    (SELECT COUNT(*) FROM upload_active) AS users_with_new_transactions_30d,
    (SELECT COUNT(*) FROM plaid_active)  AS users_with_plaid_sync_30d,
    (SELECT COUNT(*) FROM all_active aa JOIN users u ON u.id = aa.user_id
      WHERE u.email NOT IN ('demo@finsight.ai')) AS active_users_30d_any_signal;
-- Note: users_with_new_transactions_30d includes users whose demo clone was
-- created in the window (a signup alone creates transactions).

-- ============================================================================
-- 4. Monthly chat-active users (trend version of query 3)
-- Returns: one row per month: distinct users with a chat session created that month.
-- ============================================================================
SELECT date_trunc('month', created_at)::date AS month,
       COUNT(DISTINCT user_id)               AS chat_users
FROM chat_sessions
WHERE user_id IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- ============================================================================
-- 5a. Transactions stored: RAW (DO NOT QUOTE; includes demo clones)
-- Returns: one row, total transactions in the table.
-- ============================================================================
SELECT COUNT(*) AS transactions_raw_including_demo_clones
FROM transactions;

-- ============================================================================
-- 5b. Transactions by origin
-- Returns: one row per origin:
--   plaid       = synced from a linked bank (plaid_transaction_id set)
--   demo_clone  = matches a demo-user transaction on (date, description, amount)
--   demo_source = rows owned by the demo user itself
--   user_import = everything else (CSV/PDF upload, manual entry, seed_full.py)
-- demo_clone is a heuristic match (ESTIMATE); a real upload that happens to
-- match a demo row exactly would be miscounted, which is unlikely.
-- seed_full.py rows also land in user_import, so if you ran it against your own
-- account, subtract that account (see 5c).
-- ============================================================================
WITH demo_tx AS (
    SELECT t.transaction_date, t.description, t.amount
    FROM transactions t
    JOIN accounts a ON a.id = t.account_id
    JOIN users u    ON u.id = a.user_id
    WHERE u.email = 'demo@finsight.ai'
),
labelled AS (
    SELECT t.id,
           CASE
             WHEN u.email = 'demo@finsight.ai'        THEN 'demo_source'
             WHEN t.plaid_transaction_id IS NOT NULL  THEN 'plaid'
             WHEN EXISTS (SELECT 1 FROM demo_tx d
                          WHERE d.transaction_date = t.transaction_date
                            AND d.description      = t.description
                            AND d.amount           = t.amount) THEN 'demo_clone'
             ELSE 'user_import'
           END AS origin
    FROM transactions t
    JOIN accounts a ON a.id = t.account_id
    JOIN users u    ON u.id = a.user_id
)
SELECT origin, COUNT(*) AS transactions
FROM labelled
GROUP BY origin
ORDER BY transactions DESC;

-- ============================================================================
-- 5c. Real (non-demo) transactions per user
-- Returns: one row per user with plaid + user_import counts. Use it to see
-- whether the "real" total is dominated by your own account.
-- ============================================================================
WITH demo_tx AS (
    SELECT t.transaction_date, t.description, t.amount
    FROM transactions t
    JOIN accounts a ON a.id = t.account_id
    JOIN users u    ON u.id = a.user_id
    WHERE u.email = 'demo@finsight.ai'
)
SELECT u.id AS user_id,
       COUNT(*) FILTER (WHERE t.plaid_transaction_id IS NOT NULL) AS plaid_tx,
       COUNT(*) FILTER (WHERE t.plaid_transaction_id IS NULL)     AS imported_tx
FROM transactions t
JOIN accounts a ON a.id = t.account_id
JOIN users u    ON u.id = a.user_id
WHERE u.email <> 'demo@finsight.ai'
  AND NOT EXISTS (SELECT 1 FROM demo_tx d
                  WHERE d.transaction_date = t.transaction_date
                    AND d.description      = t.description
                    AND d.amount           = t.amount)
GROUP BY u.id
ORDER BY (COUNT(*)) DESC;
-- (user_id only; no emails printed. Join to users.email yourself if needed.)

-- ============================================================================
-- 6. Transactions indexed for semantic search (pgvector rows)
-- Returns: one row, embeddings stored. One embedding per transaction (ADR 0003).
-- Includes embeddings of demo clones that were later indexed.
-- ============================================================================
SELECT COUNT(*) AS transaction_embeddings
FROM transaction_embeddings;

-- ============================================================================
-- 7. Bank connections (Plaid)
-- Returns: one row per status with counts and distinct users.
-- NOTE: config default PLAID_ENV is "sandbox"; sandbox links are test banks,
-- not real customer banks. Check your Railway PLAID_ENV before quoting.
-- ============================================================================
SELECT status,
       COUNT(*)                AS connections,
       COUNT(DISTINCT user_id) AS users
FROM bank_connections
GROUP BY status;

-- ============================================================================
-- 8. Conversations (chat sessions) created
-- Returns: total sessions and sessions per month.
-- ============================================================================
SELECT COUNT(*) AS chat_sessions_total,
       COUNT(DISTINCT user_id) AS users_with_any_chat
FROM chat_sessions;

SELECT date_trunc('month', created_at)::date AS month,
       COUNT(*)                              AS chat_sessions
FROM chat_sessions
GROUP BY 1
ORDER BY 1;

-- ============================================================================
-- 9. Messages sent
-- chat_sessions.messages_json is a TEXT column holding a serialized LangChain
-- message list. Each item has "type": "human" | "ai" | "tool" | "system"
-- (see app/chat_history.py:28-33). AI items with tool_calls are tool requests,
-- not visible replies.
-- Returns: one row: user messages, assistant replies (no tool calls), tool
-- messages, and the number of sessions whose JSON failed to parse (skipped).
-- ============================================================================
WITH parsed AS (
    SELECT id,
           CASE WHEN messages_json ~ '^\s*\[' THEN messages_json::jsonb END AS msgs
    FROM chat_sessions
),
items AS (
    SELECT p.id, m
    FROM parsed p, LATERAL jsonb_array_elements(p.msgs) AS m
    WHERE p.msgs IS NOT NULL
)
SELECT
    COUNT(*) FILTER (WHERE m->>'type' = 'human')                        AS user_messages,
    COUNT(*) FILTER (WHERE m->>'type' = 'ai'
                       AND COALESCE(jsonb_array_length(m->'data'->'tool_calls'), 0) = 0
                       AND COALESCE(jsonb_array_length(m->'tool_calls'), 0) = 0) AS assistant_replies,
    COUNT(*) FILTER (WHERE m->>'type' = 'tool')                         AS tool_messages,
    (SELECT COUNT(*) FROM parsed WHERE msgs IS NULL)                    AS sessions_unparseable
FROM items;
-- If assistant_replies looks wrong, inspect one row's structure first:
--   SELECT left(messages_json, 600) FROM chat_sessions LIMIT 1;

-- ============================================================================
-- 10. Average user messages per conversation
-- Returns: one row.
-- ============================================================================
WITH per_session AS (
    SELECT cs.id,
           (SELECT COUNT(*) FROM jsonb_array_elements(cs.messages_json::jsonb) m
             WHERE m->>'type' = 'human') AS user_msgs
    FROM chat_sessions cs
    WHERE cs.messages_json ~ '^\s*\['
)
SELECT ROUND(AVG(user_msgs), 2) AS avg_user_messages_per_session,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY user_msgs) AS median_user_messages
FROM per_session;

-- ============================================================================
-- 11. Money-leak findings detected
-- Returns: one row per leak type with count, open/dismissed split and total CAD.
-- Includes findings on demo-clone data, so treat as engine output, not real
-- money saved.
-- ============================================================================
SELECT type,
       COUNT(*)                                   AS findings,
       COUNT(*) FILTER (WHERE status = 'open')    AS open_findings,
       ROUND(SUM(amount_cad)::numeric, 2)         AS total_amount_cad
FROM leak_findings
GROUP BY type
ORDER BY findings DESC;

-- ============================================================================
-- 12. Budgets, notifications and goals created
-- Returns: one row of feature-adoption counts.
-- goals live in users.goals_json (TEXT JSON array).
-- ============================================================================
SELECT
    (SELECT COUNT(*) FROM budgets)                           AS budgets,
    (SELECT COUNT(DISTINCT user_id) FROM budgets)            AS users_with_budgets,
    (SELECT COUNT(*) FROM notifications)                     AS notifications,
    (SELECT COALESCE(SUM(jsonb_array_length(goals_json::jsonb)), 0)
       FROM users WHERE goals_json ~ '^\s*\[')               AS goals,
    (SELECT COUNT(*) FROM users
      WHERE goals_json ~ '^\s*\[' AND jsonb_array_length(goals_json::jsonb) > 0) AS users_with_goals;

-- ============================================================================
-- 13. Requests per day / latency / error rate: NOT AVAILABLE IN THE DATABASE
-- No table stores HTTP requests, timings or errors (see caveat 3). The closest
-- DB-side proxy for "chat requests per day" is sessions touched per day:
-- Returns: one row per day (last 60 days) with sessions updated that day.
-- This undercounts (several messages in one session count once).
-- ============================================================================
SELECT updated_at::date AS day,
       COUNT(*)         AS chat_sessions_touched
FROM chat_sessions
WHERE updated_at >= now() - interval '60 days'
GROUP BY 1
ORDER BY 1;

-- ============================================================================
-- 14. Sanity checks (expect 0 rows written by the app; see caveat 4)
-- ============================================================================
SELECT (SELECT COUNT(*) FROM audit_log) AS audit_log_rows,
       (SELECT COUNT(*) FROM eval_runs) AS eval_runs_rows;

ROLLBACK;
