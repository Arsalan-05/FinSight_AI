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
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import type { ChatMessage, ChatSessionSummary, FinancialGoal, TransactionCitation } from "@/lib/types";

const SESSION_KEY = "finsight_chat_session";

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

function loadSessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    return localStorage.getItem(SESSION_KEY) ?? "";
  } catch {
    return "";
  }
}

function saveSessionId(id: string) {
  localStorage.setItem(SESSION_KEY, id);
}

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
  const consumedQuery = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(isSupabaseConfigured);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(() =>
    typeof window === "undefined" ? "" : loadSessionId(),
  );
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const statusIdx = useRef(0);

  useEffect(() => {
    if (!authReady) return;
    void api.getGoals().then(setGoals).catch(() => setGoals([]));
  }, [authReady]);

  const refreshSessions = useCallback(async () => {
    if (!authReady) return;
    try {
      const rows = await api.listChatSessions();
      setSessions(rows);
    } catch {
      // optional without auth
    }
  }, [authReady]);

  const loadSession = useCallback(
    async (id: string) => {
      if (!authReady) return;
      setHistoryLoading(true);
      setError(null);
      try {
        const detail = await api.getChatSession(id);
        setSessionId(detail.id);
        saveSessionId(detail.id);
        setMessages(detail.messages.map((m) => newMessage(m.role, m.content)));
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Could not load chat";
        setError(msg);
        toast(msg, "error");
      } finally {
        setHistoryLoading(false);
      }
    },
    [authReady, toast],
  );

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    Promise.all([
      api.listChatSessions().catch(() => [] as ChatSessionSummary[]),
      (async () => {
        const saved = loadSessionId();
        if (!saved) return null;
        try {
          return await api.getChatSession(saved);
        } catch {
          localStorage.removeItem(SESSION_KEY);
          return null;
        }
      })(),
    ])
      .then(([rows, detail]) => {
        if (!active) return;
        setSessions(rows);
        if (detail) {
          setSessionId(detail.id);
          setMessages(detail.messages.map((m) => newMessage(m.role, m.content)));
        }
      })
      .finally(() => {
        if (active) setHistoryLoading(false);
      });
    return () => {
      active = false;
    };
  }, [authReady]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, agentStatus]);

  const sendMessage = useCallback(
    async (text?: string) => {
      const message = (text ?? input).trim();
      if (!message || loading) return;

      setInput("");
      setError(null);
      setLoading(true);
      setAgentStatus(AGENT_STATUS[0]);

      const userMsg = newMessage("user", message);
      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "", citations: [] },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;
      const fallbackTimer = setInterval(() => {
        statusIdx.current = (statusIdx.current + 1) % AGENT_STATUS.length;
        setAgentStatus((prev) => prev ?? AGENT_STATUS[statusIdx.current]);
      }, 2400);

      try {
        let reply = "";
        let citations: TransactionCitation[] = [];
        let activeSession = sessionId;

        for await (const event of api.chatStream(message, sessionId || undefined, controller.signal)) {
          if (event.type === "status") {
            setAgentStatus(event.detail || event.phase);
          } else if (event.type === "token") {
            reply += event.content;
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: reply } : m)),
            );
          } else if (event.type === "done") {
            reply = event.content;
            citations = event.citations ?? [];
            activeSession = event.session_id;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: reply, citations } : m,
              ),
            );
          } else if (event.type === "error") {
            throw new Error(event.message);
          }
        }

        if (activeSession) {
          setSessionId(activeSession);
          saveSessionId(activeSession);
          void refreshSessions();
        }
      } catch (e) {
        if (controller.signal.aborted) return;
        const msg = e instanceof Error ? e.message : "Chat failed";
        setError(msg);
        toast(msg, "error");
        setMessages((prev) => prev.filter((m) => m.id !== assistantId));
      } finally {
        clearInterval(fallbackTimer);
        setLoading(false);
        setAgentStatus(null);
        abortRef.current = null;
        inputRef.current?.focus();
      }
    },
    [input, loading, sessionId, toast, refreshSessions],
  );

  useEffect(() => {
    if (!authReady || historyLoading || consumedQuery.current) return;

    const q = searchParams.get("q")?.trim();
    if (!q) return;

    consumedQuery.current = true;
    const autoSend = searchParams.get("send") !== "0";
    router.replace("/chat", { scroll: false });

    const timer = window.setTimeout(() => {
      if (autoSend) {
        void sendMessage(q);
      } else {
        setInput(q);
        inputRef.current?.focus();
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, [authReady, historyLoading, searchParams, router, sendMessage]);

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
    setAgentStatus(null);
  };

  const handleNewChat = () => {
    if (loading) handleStop();
    setMessages([]);
    setError(null);
    setSessionId("");
    localStorage.removeItem(SESSION_KEY);
    inputRef.current?.focus();
  };

  const handleDeleteSession = async (id: string) => {
    const previous = sessions;
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (sessionId === id) {
      setMessages([]);
      setSessionId("");
      localStorage.removeItem(SESSION_KEY);
    }
    try {
      await api.deleteChatSession(id);
      toast("Conversation deleted");
    } catch {
      setSessions(previous);
      if (sessionId === id) void loadSession(id);
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
          sessionId={sessionId}
          loading={!authReady || historyLoading}
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
              {messages.length === 0 && !loading && !historyLoading && (
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

              {historyLoading && messages.length === 0 && (
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
                    streaming={loading && !msg.content}
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
              {loading && agentStatus && (
                <div className="mb-3">
                  <span className="status-chip">
                    <Loader2 size={11} className="animate-spin" />
                    {agentStatus}
                  </span>
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
                  disabled={loading}
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
                    disabled={!input.trim()}
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
              Answers are grounded in your transaction data — not generic estimates.
            </p>
          </div>
        ) : (
          <>
            <FormatAgentText text={content} />
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
