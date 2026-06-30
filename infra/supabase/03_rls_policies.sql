-- Row Level Security (optional hardening for Supabase-hosted Postgres)
-- Run after 02_full_schema.sql when using Supabase Auth + direct table access.
-- Note: the FastAPI backend connects as `postgres` (bypasses RLS). These policies
-- protect data if PostgREST or Supabase client access is ever enabled.

-- Helper: map auth.uid() to app users.auth_id
CREATE OR REPLACE FUNCTION public.current_app_user_id()
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT id::text FROM public.users WHERE auth_id = auth.uid()::text LIMIT 1;
$$;

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transaction_embeddings ENABLE ROW LEVEL SECURITY;

-- Users: read/update own profile
DROP POLICY IF EXISTS users_select_own ON public.users;
CREATE POLICY users_select_own ON public.users
  FOR SELECT USING (auth_id = auth.uid()::text);

DROP POLICY IF EXISTS users_update_own ON public.users;
CREATE POLICY users_update_own ON public.users
  FOR UPDATE USING (auth_id = auth.uid()::text);

-- Accounts scoped to owner
DROP POLICY IF EXISTS accounts_owner ON public.accounts;
CREATE POLICY accounts_owner ON public.accounts
  FOR ALL USING (user_id = public.current_app_user_id());

-- Transactions via account ownership
DROP POLICY IF EXISTS transactions_owner ON public.transactions;
CREATE POLICY transactions_owner ON public.transactions
  FOR ALL USING (
    account_id IN (
      SELECT id FROM public.accounts WHERE user_id = public.current_app_user_id()
    )
  );

-- Chat sessions
DROP POLICY IF EXISTS chat_sessions_owner ON public.chat_sessions;
CREATE POLICY chat_sessions_owner ON public.chat_sessions
  FOR ALL USING (user_id = public.current_app_user_id());

-- Chat messages via session
DROP POLICY IF EXISTS chat_messages_owner ON public.chat_messages;
CREATE POLICY chat_messages_owner ON public.chat_messages
  FOR ALL USING (
    session_id IN (
      SELECT id FROM public.chat_sessions WHERE user_id = public.current_app_user_id()
    )
  );

-- Embeddings via transaction ownership
DROP POLICY IF EXISTS embeddings_owner ON public.transaction_embeddings;
CREATE POLICY embeddings_owner ON public.transaction_embeddings
  FOR ALL USING (
    transaction_id IN (
      SELECT t.id FROM public.transactions t
      JOIN public.accounts a ON a.id = t.account_id
      WHERE a.user_id = public.current_app_user_id()
    )
  );
