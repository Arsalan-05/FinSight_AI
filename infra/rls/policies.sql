-- FinSight AI — Row-Level Security policies (Supabase Auth)
-- Apply after schema exists. FastAPI as `postgres` bypasses RLS; these protect
-- PostgREST / client-side access as defense-in-depth.
-- Pattern: auth.uid() → users.auth_id → users.id (app user_id)

CREATE OR REPLACE FUNCTION public.current_app_user_id()
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT id::text
  FROM public.users
  WHERE auth_id = auth.uid()::text
  LIMIT 1;
$$;

-- ── Enable RLS ───────────────────────────────────────────────────────────────

ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.leak_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- ── accounts ─────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS accounts_select_own ON public.accounts;
CREATE POLICY accounts_select_own ON public.accounts
  FOR SELECT USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS accounts_insert_own ON public.accounts;
CREATE POLICY accounts_insert_own ON public.accounts
  FOR INSERT WITH CHECK (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS accounts_update_own ON public.accounts;
CREATE POLICY accounts_update_own ON public.accounts
  FOR UPDATE USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS accounts_delete_own ON public.accounts;
CREATE POLICY accounts_delete_own ON public.accounts
  FOR DELETE USING (user_id = public.current_app_user_id());

-- ── transactions (via account ownership) ─────────────────────────────────────

DROP POLICY IF EXISTS transactions_select_own ON public.transactions;
CREATE POLICY transactions_select_own ON public.transactions
  FOR SELECT USING (
    account_id IN (
      SELECT id FROM public.accounts WHERE user_id = public.current_app_user_id()
    )
  );

DROP POLICY IF EXISTS transactions_insert_own ON public.transactions;
CREATE POLICY transactions_insert_own ON public.transactions
  FOR INSERT WITH CHECK (
    account_id IN (
      SELECT id FROM public.accounts WHERE user_id = public.current_app_user_id()
    )
  );

DROP POLICY IF EXISTS transactions_update_own ON public.transactions;
CREATE POLICY transactions_update_own ON public.transactions
  FOR UPDATE USING (
    account_id IN (
      SELECT id FROM public.accounts WHERE user_id = public.current_app_user_id()
    )
  );

DROP POLICY IF EXISTS transactions_delete_own ON public.transactions;
CREATE POLICY transactions_delete_own ON public.transactions
  FOR DELETE USING (
    account_id IN (
      SELECT id FROM public.accounts WHERE user_id = public.current_app_user_id()
    )
  );

-- ── chat_sessions ────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS chat_sessions_select_own ON public.chat_sessions;
CREATE POLICY chat_sessions_select_own ON public.chat_sessions
  FOR SELECT USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS chat_sessions_insert_own ON public.chat_sessions;
CREATE POLICY chat_sessions_insert_own ON public.chat_sessions
  FOR INSERT WITH CHECK (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS chat_sessions_update_own ON public.chat_sessions;
CREATE POLICY chat_sessions_update_own ON public.chat_sessions
  FOR UPDATE USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS chat_sessions_delete_own ON public.chat_sessions;
CREATE POLICY chat_sessions_delete_own ON public.chat_sessions
  FOR DELETE USING (user_id = public.current_app_user_id());

-- ── leak_findings ────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS leak_findings_select_own ON public.leak_findings;
CREATE POLICY leak_findings_select_own ON public.leak_findings
  FOR SELECT USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS leak_findings_insert_own ON public.leak_findings;
CREATE POLICY leak_findings_insert_own ON public.leak_findings
  FOR INSERT WITH CHECK (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS leak_findings_update_own ON public.leak_findings;
CREATE POLICY leak_findings_update_own ON public.leak_findings
  FOR UPDATE USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS leak_findings_delete_own ON public.leak_findings;
CREATE POLICY leak_findings_delete_own ON public.leak_findings
  FOR DELETE USING (user_id = public.current_app_user_id());

-- ── budgets ──────────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS budgets_select_own ON public.budgets;
CREATE POLICY budgets_select_own ON public.budgets
  FOR SELECT USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS budgets_insert_own ON public.budgets;
CREATE POLICY budgets_insert_own ON public.budgets
  FOR INSERT WITH CHECK (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS budgets_update_own ON public.budgets;
CREATE POLICY budgets_update_own ON public.budgets
  FOR UPDATE USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS budgets_delete_own ON public.budgets;
CREATE POLICY budgets_delete_own ON public.budgets
  FOR DELETE USING (user_id = public.current_app_user_id());

-- ── notifications ────────────────────────────────────────────────────────────

DROP POLICY IF EXISTS notifications_select_own ON public.notifications;
CREATE POLICY notifications_select_own ON public.notifications
  FOR SELECT USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS notifications_insert_own ON public.notifications;
CREATE POLICY notifications_insert_own ON public.notifications
  FOR INSERT WITH CHECK (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS notifications_update_own ON public.notifications;
CREATE POLICY notifications_update_own ON public.notifications
  FOR UPDATE USING (user_id = public.current_app_user_id());

DROP POLICY IF EXISTS notifications_delete_own ON public.notifications;
CREATE POLICY notifications_delete_own ON public.notifications
  FOR DELETE USING (user_id = public.current_app_user_id());
