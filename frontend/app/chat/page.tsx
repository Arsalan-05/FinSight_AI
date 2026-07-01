"use client";

import {
  BarChart3,
  BrainCircuit,
  Globe,
  Loader2,
  MessageSquarePlus,
  Receipt,
  Send,
  Sparkles,
  StopCircle,
  Target,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ChatHistorySidebar } from "@/components/chat/ChatHistorySidebar";
import { FormatAgentText } from "@/components/chat/formatAgentText";
import { PageHeader } from "@/components/ui/PageHeader";
import { useChatStream } from "@/contexts/ChatStreamContext";
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import {
  clearChatDraft,
  clearSessionId,
  hydrateSessionState,
  loadChatDraft,
  loadSessionId,
  recoverSessionFromApi,
  resolveStreamId,
  saveSessionId,
  sessionLooksPending,
  sessionMigrations,
} from "@/lib/chat-stream-manager";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import type { ChatMessage, ChatSessionSummary, FinancialGoal, TransactionCitation } from "@/lib/types";

const PROMPT_GROUPS = [
  {
    icon: Receipt,
    title: "Spending analysis",
    prompt: "How much did I spend on dining last month?",
    description: "Category totals, trends, and comparisons",
  },
  {
    icon: BarChart3,
    title: "Subscriptions",
    prompt: "What are my recurring subscriptions costing per month?",
    description: "Detect recurring charges and monthly burn",
  },
  {
    icon: Target,
    title: "Savings plan",
    prompt: "Based on my spending, where should I cut back?",
    description: "Personalized recommendations from your data",
  },
  {
    icon: Globe,
    title: "Market & policy",
    prompt: "What's the 2026 TFSA contribution limit in Canada?",
    description: "Live web search plus your account context",
  },
];

const AGENT_STATUS = [
  "Reviewing your accounts…",
  "Querying transaction history…",
  "Running spending analysis…",
  "Searching for current rates…",
  "Synthesizing insights…",
];

function newMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return { id: crypto.randomUUID(), role, content };
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="page-container flex min-h-[50vh] items-center justify-center text-sm text-[var(--muted)]">
          Loading advisor…
        </div>
      }
    >
      <ChatPageContent />
    </Suspense>
  );
}

function ChatPageContent() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { version, getSessionState, sendMessage: sendStream, stopSession, pendingSessionIds } =
    useChatStream();
  const consumedQueryKey = useRef<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(isSupabaseConfigured);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chatAvailable, setChatAvailable] = useState(true);
  const [chatUnavailableReason, setChatUnavailableReason] = useState<string | null>(null);
  const [slowHint, setSlowHint] = useState(false);
  const [viewSessionId, setViewSessionId] = useState(() =>
    typeof window === "undefined" ? "" : loadSessionId(),
  );
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const sidebarActiveId = viewSessionId.startsWith("new:")
    ? resolveStreamId(viewSessionId)
    : viewSessionId;

  const refreshSessions = useCallback(async () => {
    if (!authReady) return;
    try {
      const rows = await api.listChatSessions();
      setSessions(rows);
    } catch {
      // optional without auth
    }
  }, [authReady]);

  const applyView = useCallback(
    async (id: string, opts?: { fetchFromApi?: boolean }) => {
      setError(null);
      setViewSessionId(id);

      if (!id) {
        setMessages([]);
        setLoading(false);
        setAgentStatus(null);
        return;
      }

      const live = getSessionState(id);
      if (live) {
        setMessages(live.messages);
        setLoading(live.loading);
        setAgentStatus(live.agentStatus);
        if (live.error) setError(live.error);
        return;
      }

      const resolved = id.startsWith("new:") ? id : resolveStreamId(id);
      const draft = loadChatDraft(resolved);
      if (draft) {
        hydrateSessionState(resolved, draft.messages);
        setMessages(draft.messages);
        setLoading(draft.loading);
        return;
      }

      if (!opts?.fetchFromApi || !authReady || id.startsWith("new:")) {
        setMessages([]);
        setLoading(false);
        setAgentStatus(null);
        return;
      }

      setConversationLoading(true);
      try {
        const detail = await Promise.race([
          api.getChatSession(id),
          new Promise<never>((_, reject) => {
            window.setTimeout(
              () => reject(new Error("Request timed out — the server may be waking up. Try again.")),
              25_000,
            );
          }),
        ]);
        const hydrated = hydrateSessionState(
          detail.id,
          detail.messages.map((m) => newMessage(m.role, m.content)),
        );
        saveSessionId(detail.id);
        setMessages(hydrated.messages);
        setLoading(hydrated.loading);
        setAgentStatus(hydrated.agentStatus);
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Could not load chat";
        setError(msg);
        toast(msg, "error");
      } finally {
        setConversationLoading(false);
      }
    },
    [authReady, toast, getSessionState],
  );

  useEffect(() => {
    if (!viewSessionId) return;

    if (viewSessionId.startsWith("new:")) {
      const migrated = sessionMigrations.get(viewSessionId);
      if (migrated) {
        setViewSessionId(migrated);
        saveSessionId(migrated);
        return;
      }
    }

    const live = getSessionState(viewSessionId);
    if (!live) return;

    setMessages(live.messages);
    setLoading(live.loading);
    setAgentStatus(live.agentStatus);
    if (live.error) setError(live.error);
    else setError(null);
  }, [version, viewSessionId, getSessionState]);

  useEffect(() => {
    if (!authReady) return;
    void refreshSessions();
  }, [authReady, version, refreshSessions]);

  useEffect(() => {
    void api.capabilities().then((c) => {
      const available = c.agent.chat_available !== false;
      setChatAvailable(available);
      setChatUnavailableReason(
        available ? null : (c.agent.chat_unavailable_reason ?? "Advisor is unavailable on this deployment."),
      );
    }).catch(() => {
      setChatAvailable(true);
    });
    void api.health().catch(() => {});
  }, []);

  useEffect(() => {
    if (!loading) {
      setSlowHint(false);
      return;
    }
    const timer = window.setTimeout(() => setSlowHint(true), 12_000);
    return () => window.clearTimeout(timer);
  }, [loading]);

  useEffect(() => {
    if (!authReady) return;
    void api.getGoals().then(setGoals).catch(() => setGoals([]));
  }, [authReady]);

  const loadSession = useCallback(
    (id: string) => {
      if (!authReady) return;
      saveSessionId(id);
      void applyView(id, { fetchFromApi: true });
    },
    [authReady, applyView],
  );

  useEffect(() => {
    if (!authReady || !viewSessionId || viewSessionId.startsWith("new:")) return;

    const draftPending = loadChatDraft(viewSessionId)?.loading;
    const pending =
      loading ||
      draftPending ||
      pendingSessionIds.includes(viewSessionId) ||
      sessionLooksPending(messages);

    if (!pending) return;

    let cancelled = false;
    const tick = async () => {
      const recovered = await recoverSessionFromApi(viewSessionId);
      if (cancelled || !recovered) return;
      setMessages(recovered.messages);
      setLoading(recovered.loading);
      setAgentStatus(recovered.agentStatus);
      if (!recovered.loading) {
        setError(null);
        void refreshSessions();
      }
    };
    const interval = window.setInterval(() => void tick(), 2000);
    void tick();
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [authReady, viewSessionId, loading, messages, pendingSessionIds, refreshSessions]);

  useEffect(() => {
    if (!authReady) return;

    let active = true;
    setSessionsLoading(true);
    void api
      .listChatSessions()
      .then((rows) => {
        if (active) setSessions(rows);
      })
      .catch(() => {
        if (active) setSessions([]);
      })
      .finally(() => {
        if (active) setSessionsLoading(false);
      });

    if (searchParams.get("q")?.trim()) {
      return () => {
        active = false;
      };
    }

    const saved = loadSessionId();
    if (saved && !saved.startsWith("new:")) {
      void applyView(saved, { fetchFromApi: true });
    }

    return () => {
      active = false;
    };
  }, [authReady, searchParams, applyView]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, agentStatus]);

  const sendMessage = useCallback(
    async (text?: string, options?: { newSession?: boolean }) => {
      const message = (text ?? input).trim();
      if (!message) return;

      const isNew = Boolean(options?.newSession);
      let activeId = "";
      if (!isNew && viewSessionId) {
        if (viewSessionId.startsWith("new:")) {
          const migrated = sessionMigrations.get(viewSessionId);
          if (migrated) {
            activeId = migrated;
          } else if (getSessionState(viewSessionId)?.loading) {
            return;
          }
        } else {
          activeId = viewSessionId;
        }
      }
      if (activeId && getSessionState(activeId)?.loading) return;

      setInput("");
      setError(null);
      setLoading(true);
      setAgentStatus(AGENT_STATUS[0]);

      const priorMessages = isNew
        ? []
        : messages.filter((m) => m.content.trim() || m.role === "user");

      const streamKey = await sendStream(message, {
        sessionId: activeId || undefined,
        newSession: isNew,
        priorMessages,
      });

      setViewSessionId(streamKey);
      if (!streamKey.startsWith("new:")) {
        saveSessionId(streamKey);
      }

      const live = getSessionState(streamKey);
      if (live) {
        setMessages(live.messages);
        setLoading(live.loading);
        setAgentStatus(live.agentStatus);
      }

      void refreshSessions();
      inputRef.current?.focus();
    },
    [input, viewSessionId, messages, sendStream, getSessionState, refreshSessions],
  );

  useEffect(() => {
    if (!authReady || sessionsLoading) return;

    const q = searchParams.get("q")?.trim();
    if (!q) {
      consumedQueryKey.current = null;
      return;
    }

    const consumeKey = searchParams.toString();
    if (consumedQueryKey.current === consumeKey) return;
    consumedQueryKey.current = consumeKey;

    const autoSend = searchParams.get("send") !== "0";
    const startNewChat = searchParams.get("new") !== "0";

    if (startNewChat) {
      clearSessionId();
      void applyView("");
    }

    router.replace("/chat", { scroll: false });

    const timer = window.setTimeout(() => {
      if (autoSend) {
        void sendMessage(q, { newSession: startNewChat });
      } else {
        setInput(q);
        inputRef.current?.focus();
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, [authReady, sessionsLoading, searchParams, router, sendMessage, applyView]);

  const handleStop = () => {
    if (!viewSessionId) return;
    stopSession(viewSessionId);
    const resolved = resolveStreamId(viewSessionId);
    if (resolved !== viewSessionId) stopSession(resolved);
    setLoading(false);
    setAgentStatus(null);
  };

  const handleNewChat = () => {
    clearSessionId();
    void applyView("");
    inputRef.current?.focus();
  };

  const handleDeleteSession = async (id: string) => {
    const previous = sessions;
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (viewSessionId === id || sidebarActiveId === id) {
      clearSessionId();
      void applyView("");
    }
    try {
      await api.deleteChatSession(id);
      toast("Conversation deleted");
    } catch {
      setSessions(previous);
      if (viewSessionId === id) void applyView(id, { fetchFromApi: true });
      toast("Could not delete conversation", "error");
    }
  };

  const handleTogglePin = async (s: ChatSessionSummary) => {
    try {
      const updated = await api.updateChatSession(s.id, { pinned: !s.pinned });
      setSessions((prev) => {
        const next = prev.map((x) => (x.id === s.id ? updated : x));
        return [...next].sort((a, b) => {
          if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
          return (b.updated_at ?? "").localeCompare(a.updated_at ?? "");
        });
      });
    } catch {
      toast("Could not update conversation", "error");
    }
  };

  const startRename = (s: ChatSessionSummary) => {
    setRenamingId(s.id);
    setRenameValue(s.title);
  };

  const commitRename = async (id: string) => {
    const title = renameValue.trim();
    setRenamingId(null);
    if (!title) return;
    try {
      const updated = await api.updateChatSession(id, { title });
      setSessions((prev) => prev.map((x) => (x.id === id ? updated : x)));
    } catch {
      toast("Could not rename conversation", "error");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  };

  return (
    <div className="page-container max-w-7xl">
      <PageHeader
        eyebrow="AI Advisor"
        title="Finance"
        titleAccent="Advisor"
        subtitle="Ask questions about your spending, savings, and goals — answers use your real transaction data."
        actions={
          <button
            type="button"
            onClick={handleNewChat}
            className="btn-ghost inline-flex items-center gap-2 px-4 py-2 text-sm"
          >
            <MessageSquarePlus size={15} />
            New chat
          </button>
        }
      />

      <div className="chat-shell">
        <ChatHistorySidebar
          sessions={sessions}
          sessionId={sidebarActiveId}
          streamingSessionIds={pendingSessionIds}
          loading={!authReady || sessionsLoading}
          renamingId={renamingId}
          renameValue={renameValue}
          onNewChat={handleNewChat}
          onSelect={(id) => void loadSession(id)}
          onRenameStart={startRename}
          onRenameChange={setRenameValue}
          onRenameCommit={(id) => void commitRename(id)}
          onRenameCancel={() => setRenamingId(null)}
          onTogglePin={(s) => void handleTogglePin(s)}
          onDelete={(id) => void handleDeleteSession(id)}
        />

        <div className="chat-main">
          <div className="chat-panel panel">
            <div className="chat-panel-header">
              <div className="agent-avatar shrink-0">
                <BrainCircuit size={16} className="text-[var(--accent)]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-[var(--foreground)]">FinSight Advisor</p>
                <p className="truncate text-[11px] text-[var(--muted)]">
                  Grounded in your transactions and goals
                </p>
              </div>
              <span className="status-chip shrink-0">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Ready
              </span>
            </div>

            <div className="chat-messages">
              {messages.length === 0 && !loading && !conversationLoading && (
                <div className="flex flex-1 flex-col items-center justify-center gap-8 py-6">
                  <div className="text-center">
                    <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent-soft)] glow-accent">
                      <Sparkles size={26} className="text-[var(--accent)]" />
                    </div>
                    <h2 className="text-lg font-semibold text-[var(--foreground)]">
                      Your personal finance analyst
                    </h2>
                    <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-[var(--muted)]">
                      Ask natural questions — grounded in your transactions and financial goals.
                    </p>
                  </div>

                  {goals.length > 0 && (
                    <div className="w-full max-w-2xl rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left">
                      <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted)]">
                        Your goals
                      </p>
                      <ul className="mt-2 flex flex-wrap gap-2">
                        {goals.slice(0, 4).map((g) => (
                          <li key={g.id}>
                            <button
                              type="button"
                              onClick={() =>
                                void sendMessage(
                                  `How am I tracking toward my goal: ${g.title}?`,
                                )
                              }
                              className="capability-pill"
                            >
                              <Target size={10} className="text-[var(--accent)]" />
                              {g.title}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-2">
                    {PROMPT_GROUPS.map(({ icon: Icon, title, prompt, description }) => (
                      <button
                        key={title}
                        type="button"
                        onClick={() => void sendMessage(prompt)}
                        className="prompt-card panel-interactive"
                      >
                        <div className="prompt-card-icon">
                          <Icon size={16} />
                        </div>
                        <p className="text-sm font-medium text-[var(--foreground)]">{title}</p>
                        <p className="text-xs leading-relaxed text-[var(--muted)]">{description}</p>
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-wrap justify-center gap-2">
                    {["Cash runway", "TFSA room", "FX rates", "Anomaly detection"].map((cap) => (
                      <span key={cap} className="capability-pill">
                        <Zap size={10} className="text-[var(--accent)]" />
                        {cap}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {conversationLoading && messages.length === 0 && (
                <div className="flex flex-1 items-center justify-center gap-2 text-sm text-[var(--muted)]">
                  <Loader2 size={16} className="animate-spin text-[var(--accent)]" />
                  Loading conversation…
                </div>
              )}

              {messages.map((msg) =>
                msg.role === "user" ? (
                  <UserBubble key={msg.id} text={msg.content} />
                ) : (
                  <AgentBubble
                    key={msg.id}
                    content={msg.content}
                    citations={msg.citations}
                    streaming={loading && msg.id === messages[messages.length - 1]?.id}
                    statusText={loading && !msg.content ? agentStatus : null}
                  />
                ),
              )}

              {loading && messages[messages.length - 1]?.role !== "assistant" && (
                <AgentBubble content="" streaming statusText={agentStatus} />
              )}

              {error && (
                <p className="rounded-xl border border-rose-500/25 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
                  {error}
                </p>
              )}
              <div ref={bottomRef} />
            </div>

            <div className="chat-composer">
              {!chatAvailable && chatUnavailableReason && (
                <p className="mb-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--muted)]">
                  {chatUnavailableReason}
                </p>
              )}
              {loading && agentStatus && (
                <div className="mb-3 space-y-2">
                  <span className="status-chip">
                    <Loader2 size={11} className="animate-spin" />
                    {agentStatus}
                  </span>
                  {slowHint && (
                    <p className="text-xs text-[var(--muted)]">
                      Still working — free-tier servers can take up to a minute on the first
                      request after idle. Leaving this page is fine; the answer will save when ready.
                    </p>
                  )}
                </div>
              )}
              <div className="chat-composer-inner">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about spending, savings, subscriptions, TFSA, or market rates…"
                  rows={1}
                  disabled={loading || !chatAvailable}
                  className="max-h-32 min-h-[2.5rem] flex-1 resize-none bg-transparent py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none disabled:opacity-50"
                />
                {loading ? (
                  <button
                    type="button"
                    onClick={handleStop}
                    aria-label="Stop generating"
                    className="mb-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-[var(--muted)] hover:bg-[var(--surface-elevated)] hover:text-[var(--foreground)]"
                  >
                    <StopCircle size={18} />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => void sendMessage()}
                    disabled={!input.trim() || !chatAvailable}
                    aria-label="Send message"
                    className="btn-primary mb-1 flex h-9 w-9 shrink-0 items-center justify-center disabled:opacity-40"
                  >
                    <Send size={15} />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="user-bubble">{text}</div>
    </div>
  );
}

function AgentBubble({
  content,
  citations,
  streaming,
  statusText,
}: {
  content: string;
  citations?: TransactionCitation[];
  streaming?: boolean;
  statusText?: string | null;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="agent-avatar mt-0.5">
        <BrainCircuit size={14} className="text-[var(--accent)]" />
      </div>
      <div className="agent-bubble">
        {streaming && !content ? (
          <div className="flex flex-col gap-2">
            <span className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <Loader2 size={14} className="animate-spin text-[var(--accent)]" />
              {statusText ?? "Analyzing your finances…"}
            </span>
            <p className="text-[11px] text-[var(--muted)] opacity-80">
              Checking your data — the answer will type in when ready.
            </p>
          </div>
        ) : (
          <>
            <FormatAgentText text={content} />
            {streaming && (
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-[var(--accent)] align-middle" />
            )}
            {citations && citations.length > 0 && (
              <div className="mt-4 border-t border-[var(--border)] pt-3">
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                  Source transactions
                </p>
                <div className="flex flex-col gap-1.5">
                  {citations.map((c) => (
                    <div key={c.id} className="citation-chip">
                      <Receipt size={12} className="shrink-0 text-[var(--accent)]" />
                      <span className="truncate text-[var(--foreground)]">
                        {c.description ?? c.merchant}
                      </span>
                      <span className="ml-auto shrink-0 text-[var(--muted)]">{c.date ?? "—"}</span>
                      {c.amount != null && (
                        <span
                          className={[
                            "shrink-0 font-medium tabular-nums",
                            c.amount < 0 ? "text-rose-400" : "text-emerald-400",
                          ].join(" ")}
                        >
                          {c.amount < 0 ? "-" : "+"}${Math.abs(c.amount).toFixed(2)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
