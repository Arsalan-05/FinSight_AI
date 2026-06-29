import type {
  Account,
  ChatSessionDetail,
  ChatSessionSummary,
  ChatSSEEvent,
  FinancialGoal,
  HealthResponse,
  DbHealthResponse,
  InsightsResponse,
  SearchResponse,
  Transaction,
  TransactionList,
  User,
} from "./types";
import { authHeaders } from "./auth";
import { getAccessTokenReady } from "./supabase/session";
import { isSupabaseConfigured } from "./supabase/client";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const PUBLIC_PATHS = new Set(["/health", "/health/db"]);

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
  return res.json() as Promise<T>;
}

// ── Health ─────────────────────────────────────────────────────────────────

export const api = {
  health: (): Promise<HealthResponse> => request("/health"),

  healthDb: (): Promise<DbHealthResponse> => request("/health/db"),

  getMe: (): Promise<User> => request("/auth/me"),

  syncProfile: (): Promise<User> => request("/auth/sync", { method: "POST" }),

  // ── Users ───────────────────────────────────────────────────────────────

  getUsers: (): Promise<User[]> => request("/users/"),
  createUser: (data: { email: string; name: string }): Promise<User> =>
    request("/users/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // ── Accounts ────────────────────────────────────────────────────────────

  getAccounts: (): Promise<Account[]> => request("/accounts/"),
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

  listChatSessions: (): Promise<ChatSessionSummary[]> => request("/chat/sessions"),

  getChatSession: (id: string): Promise<ChatSessionDetail> =>
    request(`/chat/sessions/${id}`),

  deleteChatSession: (id: string): Promise<void> =>
    request(`/chat/sessions/${id}`, { method: "DELETE" }),

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
