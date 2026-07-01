export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface Account {
  id: string;
  user_id: string;
  name: string;
  institution: string;
  account_type: "checking" | "savings" | "credit";
  created_at: string;
  plaid_linked?: boolean;
  last_synced_at?: string | null;
}

export interface Transaction {
  id: string;
  account_id: string;
  transaction_date: string;
  description: string;
  amount: number;
  category: string;
  merchant: string | null;
  notes: string | null;
  created_at: string;
}

export interface TransactionList {
  total: number;
  items: Transaction[];
}

export interface SearchResponse {
  results: Transaction[];
  query: string;
  k: number;
  embedding_enabled: boolean;
}

export interface SearchStatusResponse {
  embedding_enabled: boolean;
  transaction_count: number;
  indexed_count: number;
  needs_reindex: boolean;
}

export interface ReindexResponse {
  indexed: number;
  transaction_count: number;
  indexed_count: number;
  remaining: number;
  complete: boolean;
}

export interface HealthResponse {
  status: string;
  environment: string;
  version?: string;
  llm_provider?: string;
}

export interface CapabilitiesResponse {
  product: string;
  version: string;
  environment: string;
  stack: Record<string, string>;
  agent: {
    tool_count: number;
    tools: string[];
    features: string[];
    max_tool_rounds: number;
    chat_available?: boolean;
    chat_unavailable_reason?: string | null;
  };
  integrations: Record<string, boolean>;
  beta?: { invite_only: boolean };
  ops?: {
    database_host: string;
    plaid_configured: boolean;
    smtp_configured: boolean;
    embeddings_configured: boolean;
    llm_configured: boolean;
    auth_enforced: boolean;
  };
}

export interface DbHealthResponse {
  connected: boolean;
  using_supabase_postgres: boolean;
  using_fallback?: boolean;
  use_supabase_db: boolean;
  host: string;
  error?: string | null;
}

export interface BootstrapResponse {
  user_id: string;
  email: string;
  name: string;
  provisioned_demo: boolean;
  db_connected: boolean;
  db_host: string;
  using_fallback: boolean;
  db_error: string | null;
  account_count: number;
  transaction_count: number;
}

export interface PlaidStatus {
  enabled: boolean;
  environment: string | null;
}

export interface BankConnection {
  id: string;
  institution_name: string;
  institution_id: string | null;
  status: string;
  last_synced_at: string | null;
  created_at: string;
}

export interface PlaidSyncResult {
  connection_id: string;
  institution: string;
  added?: number;
  modified_seen?: number;
  last_synced_at?: string | null;
  error?: string;
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  citations?: TransactionCitation[];
}

export interface TransactionCitation {
  id: string;
  date?: string;
  description?: string;
  amount?: number;
  category?: string;
  merchant?: string | null;
  source?: string;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  pinned: boolean;
  updated_at: string | null;
  message_count: number;
}

export interface ChatSessionDetail {
  id: string;
  title: string;
  pinned: boolean;
  messages: Array<{ role: ChatRole; content: string }>;
  updated_at: string | null;
}

export type ChatSSEEvent =
  | { type: "status"; phase: string; detail: string }
  | { type: "token"; content: string }
  | { type: "done"; session_id: string; content: string; citations?: TransactionCitation[] }
  | { type: "error"; message: string };

export interface InsightCard {
  id: string;
  severity: "info" | "warning" | "success";
  title: string;
  body: string;
  action: string | null;
}

export interface InsightsResponse {
  generated_at: string;
  insight_cards: InsightCard[];
  subscriptions: { count: number; estimated_monthly_total: number };
  cash_runway: { runway_months: number | null; message: string };
  tfsa_rrsp: { tfsa: { remaining_room: number; limit: number; estimated_contributions: number } };
}

export interface WeeklyBrief {
  generated_at: string;
  week_start: string;
  week_end: string;
  headline: string;
  this_week_spend: number;
  prev_week_spend: number;
  spend_change_pct: number | null;
  sections: Array<{ id: string; label: string; value: string }>;
  alerts: Array<{ id: string; severity: string; title: string; body: string }>;
  tfsa: { limit: number; estimated_contributions: number; remaining_room: number; note?: string };
  subscriptions_monthly: number;
}

export interface Budget {
  id: string;
  category: string;
  monthly_limit: number;
  created_at: string;
  spent_this_month: number;
  percent_used: number;
}

export interface AppNotification {
  id: string;
  kind: string;
  severity: string;
  title: string;
  body: string;
  read: boolean;
  created_at: string;
}

export interface AlertPreferences {
  spend_alerts: boolean;
  email_digest: boolean;
}

export interface SubscriptionItem {
  merchant: string;
  category: string;
  amount: number;
  occurrences: number;
  last_date: string;
  estimated_monthly: number;
  transaction_ids: string[];
}

export interface SubscriptionsResponse {
  items: SubscriptionItem[];
  summary: { count: number; estimated_monthly_total: number };
}

export interface FinancialGoal {
  id: string;
  title: string;
  target_amount?: number | null;
  current_amount?: number | null;
  deadline?: string | null;
  notes?: string | null;
  status: string;
  created_at: string;
  updated_at?: string | null;
}

export interface CategoryRule {
  id: string;
  match: string;
  value: string;
  category: string;
}

export interface AgentLearnedProfile {
  learned_summary?: string;
  preferences?: string[];
  risk_flags?: string[];
  updated_at?: string | null;
}

export const CATEGORY_COLORS: Record<string, string> = {
  Dining: "#f59e0b",
  Groceries: "#22c55e",
  Transport: "#3b82f6",
  Housing: "#8b5cf6",
  Shopping: "#ec4899",
  Subscriptions: "#6366f1",
  Healthcare: "#14b8a6",
  Income: "#10b981",
  Entertainment: "#f97316",
  Utilities: "#64748b",
  Uncategorized: "#6b7280",
};

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] ?? "#6b7280";
}
