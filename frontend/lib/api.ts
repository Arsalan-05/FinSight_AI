import type {
  Account,
  AgentLearnedProfile,
  AlertPreferences,
  AppNotification,
  Budget,
  CategoryRule,
  ChatSessionDetail,
  ChatSessionSummary,
  ChatSSEEvent,
  BootstrapResponse,
  CapabilitiesResponse,
  EvalRunSummary,
  FinancialGoal,
  ForecastRequest,
  ForecastResult,
  BankConnection,
  LeakDraft,
  LeakFinding,
  LeakSummary,
  OsapPlanRequest,
  PlaidSyncResult,
  PlaidStatus,
  HealthResponse,
  DbHealthResponse,
  InsightsResponse,
  DashboardResponse,
  RegisteredOptimizerRequest,
  SearchResponse,
  SearchStatusResponse,
  ReindexResponse,
  SubscriptionsResponse,
  Transaction,
  TransactionList,
  User,
  WeeklyBrief,
} from "./types";
import { authHeaders } from "./auth";
import { getAccessTokenReady } from "./supabase/session";
import { isSupabaseConfigured } from "./supabase/client";

/**
 * API base URL for browser fetches.
 *
 * Production (Railway): set NEXT_PUBLIC_API_URL=/backend so the browser only
 * talks to the same origin as the website. Next.js rewrites /backend → API
 * (API_PROXY_TARGET). That matches how single-service Railway apps feel fast/reliable.
 *
 * Local: NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 (direct) or /backend with proxy.
 */
const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const PUBLIC_PATHS = new Set(["/health", "/health/db", "/capabilities"]);

function parseJsonBody<T>(text: string, path: string): T {
  const trimmed = text.trimStart();
  if (trimmed.startsWith("<") || trimmed.startsWith("<!")) {
    throw new Error(
      `API returned a web page for ${path}. If using the proxy, set NEXT_PUBLIC_API_URL=/backend ` +
        `and API_PROXY_TARGET to the Railway API URL. Currently BASE=${BASE || "(empty)"}`,
    );
  }
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(
      `API returned non-JSON for ${path}. Check NEXT_PUBLIC_API_URL (currently: ${BASE || "(empty)"}).`,
    );
  }
}

async function buildHeaders(path: string, extra?: HeadersInit): Promise<HeadersInit> {
  const needsAuth = isSupabaseConfigured() && !PUBLIC_PATHS.has(path);
  const token = needsAuth ? await getAccessTokenReady() : null;
  if (needsAuth && !token) {
    throw new Error("Session not ready — sign in again or refresh the page.");
  }
  return {
    "Content-Type": "application/json",
    ...authHeaders(),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  // Keep trailing slashes — FastAPI list routes are mounted at "/accounts/", etc.
  // Next skipTrailingSlashRedirect prevents /backend/.../ from 308-stripping auth.
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: await buildHeaders(path, init?.headers),
      ...init,
    });
  } catch (e) {
    const raw = e instanceof Error ? e.message : String(e);
    // Safari: "Load failed" · Chrome: "Failed to fetch"
    if (/load failed|failed to fetch|networkerror|network request failed/i.test(raw)) {
      throw new Error(
        "Could not reach the API through this site. On Railway, set NEXT_PUBLIC_API_URL=/backend " +
          "and API_PROXY_TARGET to the API service URL, then redeploy the frontend. " +
          `BASE=${BASE || "(empty)"}`,
      );
    }
    throw e instanceof Error ? e : new Error(raw || "Request failed");
  }
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    if (text.includes("Service Suspended") || text.trimStart().startsWith("<")) {
      throw new Error(
        "API unavailable — check Railway API service and that NEXT_PUBLIC_API_URL points at the API, not the frontend.",
      );
    }
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return parseJsonBody<T>(text, path);
}

async function requestWithRetry<T>(
  path: string,
  init?: RequestInit,
  attempts = 3,
): Promise<T> {
  let lastError: unknown;
  for (let i = 0; i < attempts; i += 1) {
    try {
      return await request<T>(path, init);
    } catch (e) {
      lastError = e;
      if (i === attempts - 1) break;
      await new Promise((resolve) => setTimeout(resolve, 800 * (i + 1)));
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Request failed");
}

// ── Health ─────────────────────────────────────────────────────────────────

export const api = {
  health: (): Promise<HealthResponse> => request("/health"),

  healthDb: (): Promise<DbHealthResponse> => request("/health/db"),

  capabilities: (): Promise<CapabilitiesResponse> => request("/capabilities"),

  getDashboard: (): Promise<DashboardResponse> => request("/dashboard/"),

  getMe: (): Promise<User> => request("/auth/me"),

  syncProfile: (): Promise<User> => request("/auth/sync", { method: "POST" }),

  bootstrap: (): Promise<BootstrapResponse> =>
    request("/auth/bootstrap", { method: "POST" }),

  // ── Users ───────────────────────────────────────────────────────────────

  getUsers: (): Promise<User[]> => request("/users/"),
  createUser: (data: { email: string; name: string }): Promise<User> =>
    request("/users/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // ── Accounts ────────────────────────────────────────────────────────────

  getAccounts: (): Promise<Account[]> => request("/accounts/"),

  getAccount: (id: string): Promise<Account> => request(`/accounts/${id}`),
  createAccount: (data: {
    user_id: string;
    name: string;
    institution: string;
    account_type: string;
  }): Promise<Account> =>
    request("/accounts/", { method: "POST", body: JSON.stringify(data) }),

  // ── Transactions ─────────────────────────────────────────────────────────

  getTransactions: (params?: {
    account_id?: string;
    category?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  }): Promise<TransactionList> => {
    const qs = new URLSearchParams();
    if (params?.account_id) qs.set("account_id", params.account_id);
    if (params?.category) qs.set("category", params.category);
    if (params?.date_from) qs.set("date_from", params.date_from);
    if (params?.date_to) qs.set("date_to", params.date_to);
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    if (params?.offset !== undefined) qs.set("offset", String(params.offset));
    const q = qs.toString();
    return request(q ? `/transactions/?${q}` : "/transactions/");
  },

  createTransaction: (data: {
    account_id: string;
    transaction_date: string;
    description: string;
    amount: number;
    category?: string;
    merchant?: string;
    notes?: string;
  }): Promise<Transaction> =>
    request("/transactions/", { method: "POST", body: JSON.stringify(data) }),

  deleteTransaction: (id: string): Promise<void> =>
    request(`/transactions/${id}`, { method: "DELETE" }),

  updateTransaction: (
    id: string,
    data: { category?: string; merchant?: string; notes?: string; description?: string },
  ): Promise<Transaction> =>
    request(`/transactions/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  exportMyData: (): Promise<Record<string, unknown>> => request("/auth/me/export"),

  deleteMyAccount: (): Promise<void> => request("/auth/me", { method: "DELETE" }),

  sendDigest: (): Promise<{ sent: boolean }> =>
    request("/auth/me/send-digest", { method: "POST" }),

  uploadCsv: async (
    file: File,
    account_id: string,
  ): Promise<{ created: number; errors: string[]; bank_detected?: string }> => {
    const form = new FormData();
    form.append("file", file);
    const token = await getAccessTokenReady();
    return fetch(`${BASE}/transactions/upload?account_id=${account_id}`, {
      method: "POST",
      headers: { ...authHeaders(), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: form,
    }).then((r) => {
      if (!r.ok) throw new Error(`Upload failed: ${r.statusText}`);
      return r.json() as Promise<{ created: number; errors: string[]; bank_detected?: string }>;
    });
  },

  // ── Insights & Goals ───────────────────────────────────────────────────────

  getInsights: (): Promise<InsightsResponse> => request("/insights/"),

  getWeeklyBrief: (): Promise<WeeklyBrief> => request("/insights/weekly-brief"),

  getSubscriptions: (): Promise<SubscriptionsResponse> =>
    request("/insights/subscriptions"),

  getBudgets: (): Promise<Budget[]> => request("/budgets/"),

  createBudget: (data: { category: string; monthly_limit: number }) =>
    request<Budget>("/budgets/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  deleteBudget: (id: string): Promise<void> =>
    request(`/budgets/${id}`, { method: "DELETE" }),

  getNotifications: (): Promise<AppNotification[]> => request("/notifications/"),

  markNotificationRead: (id: string) =>
    request<AppNotification>(`/notifications/${id}/read`, { method: "POST" }),

  markAllNotificationsRead: (): Promise<void> =>
    request("/notifications/read-all", { method: "POST" }),

  getAlertPreferences: (): Promise<AlertPreferences> =>
    request("/notifications/preferences"),

  updateAlertPreferences: (data: Partial<AlertPreferences>) =>
    request<AlertPreferences>("/notifications/preferences", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getGoals: (): Promise<FinancialGoal[]> => request("/goals/"),

  createGoal: (data: {
    title: string;
    target_amount?: number;
    deadline?: string;
    notes?: string;
  }): Promise<FinancialGoal> =>
    request("/goals/", { method: "POST", body: JSON.stringify(data) }),

  deleteGoal: (id: string): Promise<void> =>
    request(`/goals/${id}`, { method: "DELETE" }),

  updateGoal: (
    id: string,
    data: {
      title?: string;
      target_amount?: number;
      current_amount?: number;
      deadline?: string;
      notes?: string;
      status?: string;
    },
  ): Promise<FinancialGoal> =>
    request(`/goals/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  getLearnedProfile: (): Promise<AgentLearnedProfile> =>
    request("/auth/me/profile"),

  clearLearnedProfile: (): Promise<void> =>
    request("/auth/me/profile", { method: "DELETE" }),

  getCategoryRules: (): Promise<CategoryRule[]> => request("/transactions/rules"),

  createCategoryRule: (data: {
    value: string;
    category: string;
    match?: string;
  }): Promise<CategoryRule> =>
    request("/transactions/rules", { method: "POST", body: JSON.stringify(data) }),

  deleteCategoryRule: (id: string): Promise<void> =>
    request(`/transactions/rules/${id}`, { method: "DELETE" }),

  reapplyCategoryRules: (): Promise<{ updated: number }> =>
    request("/transactions/rules/apply", { method: "POST" }),

  // ── Bank (Plaid) ──────────────────────────────────────────────────────────

  getPlaidStatus: (): Promise<PlaidStatus> => request("/integrations/plaid/status"),

  createPlaidLinkToken: (): Promise<{ link_token: string; expiration: string }> =>
    request("/integrations/plaid/link-token", { method: "POST" }),

  exchangePlaidToken: (
    public_token: string,
    institution_name?: string,
  ): Promise<BankConnection> =>
    request("/integrations/plaid/exchange", {
      method: "POST",
      body: JSON.stringify({ public_token, institution_name }),
    }),

  listBankConnections: (): Promise<BankConnection[]> =>
    request("/integrations/plaid/connections"),

  syncBankConnections: (): Promise<PlaidSyncResult[]> =>
    request("/integrations/plaid/sync", { method: "POST" }),

  disconnectBank: (id: string): Promise<void> =>
    request(`/integrations/plaid/connections/${id}`, { method: "DELETE" }),

  listChatSessions: (): Promise<ChatSessionSummary[]> => request("/chat/sessions"),

  getChatSession: (id: string): Promise<ChatSessionDetail> =>
    requestWithRetry(`/chat/sessions/${id}`),

  deleteChatSession: (id: string): Promise<void> =>
    request(`/chat/sessions/${id}`, { method: "DELETE" }),

  updateChatSession: (
    id: string,
    data: { title?: string; pinned?: boolean },
  ): Promise<ChatSessionSummary> =>
    request(`/chat/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // ── Search ────────────────────────────────────────────────────────────────

  search: (query: string, k = 5): Promise<SearchResponse> =>
    request("/search/", {
      method: "POST",
      body: JSON.stringify({ query, k }),
    }),

  searchStatus: (): Promise<SearchStatusResponse> => request("/search/status"),

  reindexSearch: (): Promise<ReindexResponse> =>
    request("/search/reindex", { method: "POST" }),

  // ── Chat (SSE) ────────────────────────────────────────────────────────────

  chatStream: async function* (
    message: string,
    sessionId?: string,
    signal?: AbortSignal,
  ): AsyncGenerator<ChatSSEEvent> {
    const token = await getAccessTokenReady();
    const res = await fetch(`${BASE}/chat/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, session_id: sessionId }),
      signal,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = (await res.json()) as { detail?: string };
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
        detail = await res.text().catch(() => detail);
      }
      if (res.status === 429) {
        throw new Error(detail || "Too many chat requests. Please wait a moment.");
      }
      throw new Error(`API ${res.status}: ${detail}`);
    }
    if (!res.body) {
      throw new Error("No response body from chat endpoint");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const block of parts) {
        const line = block.trim();
        if (!line.startsWith("data: ")) continue;
        yield JSON.parse(line.slice(6)) as ChatSSEEvent;
      }
    }
  },

  // ── Leaks ─────────────────────────────────────────────────────────────────

  getLeaks: (rescan = true): Promise<LeakFinding[]> =>
    request(`/leaks/?rescan=${rescan ? "true" : "false"}`),

  getLeaksSummary: (): Promise<LeakSummary> => request("/leaks/summary"),

  updateLeak: (
    id: string,
    data: { status?: string; still_using?: boolean },
  ): Promise<LeakFinding> =>
    request(`/leaks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  draftLeakAction: (
    id: string,
    kind?: string,
  ): Promise<LeakDraft> =>
    request(`/leaks/${id}/draft`, {
      method: "POST",
      body: JSON.stringify(kind ? { kind } : {}),
    }),

  // ── Planner & forecast ────────────────────────────────────────────────────

  getPlannerRules: (year = 2026): Promise<Record<string, unknown>> =>
    request(`/planner/rules?year=${year}`),

  getPlannerYears: (): Promise<{ available_years: number[]; disclaimer?: string }> =>
    request("/planner/years"),

  runRegisteredOptimizer: (
    data: RegisteredOptimizerRequest,
  ): Promise<Record<string, unknown>> =>
    request("/planner/registered", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  runOsapPlan: (data: OsapPlanRequest): Promise<Record<string, unknown>> =>
    request("/planner/osap", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  runForecast: (data: ForecastRequest): Promise<ForecastResult> =>
    request("/forecast", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getForecast: (params: ForecastRequest): Promise<ForecastResult> => {
    const qs = new URLSearchParams();
    qs.set("starting_balance", String(params.starting_balance));
    qs.set("monthly_income_mean", String(params.monthly_income_mean));
    qs.set("monthly_expense_mean", String(params.monthly_expense_mean));
    if (params.monthly_income_std != null) {
      qs.set("monthly_income_std", String(params.monthly_income_std));
    }
    if (params.monthly_expense_std != null) {
      qs.set("monthly_expense_std", String(params.monthly_expense_std));
    }
    if (params.months != null) qs.set("months", String(params.months));
    if (params.n_sims != null) qs.set("n_sims", String(params.n_sims));
    if (params.seed != null) qs.set("seed", String(params.seed));
    if (params.ruin_threshold != null) {
      qs.set("ruin_threshold", String(params.ruin_threshold));
    }
    return request(`/forecast?${qs.toString()}`);
  },

  // ── Evals ─────────────────────────────────────────────────────────────────

  getEvalRuns: (): Promise<EvalRunSummary[]> => request("/evals"),

  // ── Analytics helpers ─────────────────────────────────────────────────────

  getAllTransactions: async (dateFrom: string, dateTo: string): Promise<Transaction[]> => {
    const first = await request<TransactionList>(
      `/transactions/?date_from=${dateFrom}&date_to=${dateTo}&limit=500&offset=0`,
    );
    if (first.total <= 500) return first.items;
    const pages = Math.ceil(first.total / 500);
    const rest = await Promise.all(
      Array.from({ length: pages - 1 }, (_, i) =>
        request<TransactionList>(
          `/transactions/?date_from=${dateFrom}&date_to=${dateTo}&limit=500&offset=${(i + 1) * 500}`,
        ).then((r) => r.items),
      ),
    );
    return [...first.items, ...rest.flat()];
  },
};
