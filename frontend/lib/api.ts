import type {
  Account,
  AlertPreferences,
  AppNotification,
  Budget,
  ChatSessionDetail,
  ChatSessionSummary,
  ChatSSEEvent,
  BootstrapResponse,
  CapabilitiesResponse,
  FinancialGoal,
  BankConnection,
  PlaidSyncResult,
  PlaidStatus,
  HealthResponse,
  DbHealthResponse,
  InsightsResponse,
  SearchResponse,
  SubscriptionsResponse,
  Transaction,
  TransactionList,
  User,
  WeeklyBrief,
} from "./types";
import { authHeaders } from "./auth";
import { getAccessTokenReady } from "./supabase/session";
import { isSupabaseConfigured } from "./supabase/client";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const PUBLIC_PATHS = new Set(["/health", "/health/db", "/capabilities"]);

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
  const res = await fetch(`${BASE}${path}`, {
    headers: await buildHeaders(path, init?.headers),
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

// ── Health ─────────────────────────────────────────────────────────────────

export const api = {
  health: (): Promise<HealthResponse> => request("/health"),

  healthDb: (): Promise<DbHealthResponse> => request("/health/db"),

  capabilities: (): Promise<CapabilitiesResponse> => request("/capabilities"),

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
    return request(`/transactions/${q ? `?${q}` : ""}`);
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
    request(`/chat/sessions/${id}`),

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
