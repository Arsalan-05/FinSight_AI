"use client";

import {
  BrainCircuit,
  History,
  Loader2,
  MessageSquarePlus,
  RotateCcw,
  Send,
  Sparkles,
  StopCircle,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import type { ChatMessage, ChatSessionSummary, TransactionCitation } from "@/lib/types";

const SESSION_KEY = "finsight_chat_session";

const EXAMPLE_PROMPTS = [
  "How much did I spend on dining last month?",
  "What are my subscriptions costing per month?",
  "How much TFSA room do I have left?",
  "What's my cash runway as a student?",
  "Which credit card should I use for groceries?",
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

function formatSessionDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (sameDay) {
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function ChatPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(isSupabaseConfigured);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(() =>
    typeof window === "undefined" ? "" : loadSessionId(),
  );
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const refreshSessions = useCallback(async () => {
    if (!authReady) return;
    try {
      const rows = await api.listChatSessions();
      setSessions(rows);
    } catch {
      // History is optional when auth is off in dev
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
        setMessages(
          detail.messages.map((m) => newMessage(m.role, m.content)),
        );
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
  }, [messages, loading]);

  const sendMessage = useCallback(
    async (text?: string) => {
      const message = (text ?? input).trim();
      if (!message || loading) return;

      setInput("");
      setError(null);
      setLoading(true);

      const userMsg = newMessage("user", message);
      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: assistantId, role: "assistant", content: "", citations: [] },
      ]);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        let reply = "";
        let citations: TransactionCitation[] = [];
        let activeSession = sessionId;

        for await (const event of api.chatStream(message, sessionId || undefined, controller.signal)) {
          if (event.type === "token") {
            reply += event.content;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: reply } : m,
              ),
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
        setLoading(false);
        abortRef.current = null;
        inputRef.current?.focus();
      }
    },
    [input, loading, sessionId, toast, refreshSessions],
  );

  const handleStop = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const handleNewChat = () => {
    if (loading) handleStop();
    setMessages([]);
    setError(null);
    setSessionId("");
    localStorage.removeItem(SESSION_KEY);
    inputRef.current?.focus();
  };

  const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteChatSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (sessionId === id) handleNewChat();
      toast("Conversation deleted");
    } catch {
      toast("Could not delete conversation", "error");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100dvh-4rem)] max-w-6xl gap-4">
      <aside className="hidden w-56 shrink-0 flex-col gap-2 md:flex lg:w-64">
        <button
          type="button"
          onClick={handleNewChat}
          className="flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2.5 text-sm text-zinc-300 transition-colors hover:border-zinc-700 hover:bg-zinc-800"
        >
          <MessageSquarePlus size={15} />
          New conversation
        </button>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900">
          <div className="flex items-center gap-2 border-b border-zinc-800 px-3 py-2.5">
            <History size={14} className="text-zinc-500" />
            <span className="text-xs font-medium text-zinc-400">History</span>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {!authReady || historyLoading ? (
              <div className="space-y-2 p-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="h-10 shimmer rounded-lg" />
                ))}
              </div>
            ) : sessions.length === 0 ? (
              <p className="px-2 py-4 text-center text-xs text-zinc-600">
                Past chats appear here after your first message.
              </p>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {sessions.map((s) => (
                  <li key={s.id}>
                    <div
                      className={[
                        "group flex w-full items-start gap-2 rounded-lg px-2.5 py-2 transition-colors",
                        sessionId === s.id
                          ? "bg-indigo-500/10 text-indigo-200"
                          : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200",
                      ].join(" ")}
                    >
                      <button
                        type="button"
                        onClick={() => void loadSession(s.id)}
                        className="min-w-0 flex-1 text-left"
                      >
                        <p className="truncate text-xs font-medium">{s.title}</p>
                        <p className="mt-0.5 text-[10px] text-zinc-600">
                          {formatSessionDate(s.updated_at)}
                          {s.message_count > 0 ? ` · ${s.message_count} msgs` : ""}
                        </p>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => void handleDeleteSession(s.id, e)}
                        aria-label="Delete conversation"
                        className="shrink-0 rounded p-1 text-zinc-700 opacity-0 transition-opacity hover:text-rose-400 group-hover:opacity-100"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <div className="flex shrink-0 items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-zinc-50">Finance Agent</h1>
            <p className="mt-0.5 text-sm text-zinc-500">
              Ask about your spending — answers are grounded in your transaction data
            </p>
          </div>
          <button
            type="button"
            onClick={handleNewChat}
            className="flex items-center gap-2 panel rounded-xl px-3 py-2 text-xs text-zinc-400 transition-colors hover:border-zinc-700 hover:text-zinc-200 md:hidden"
          >
            <RotateCcw size={13} />
            New chat
          </button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900">
          <div className="flex items-center gap-3 border-b border-zinc-800 px-4 py-3">
            <BrainCircuit size={16} className="text-indigo-400" />
            <span className="text-sm font-medium text-zinc-300">FinSight Agent</span>
            <span className="ml-auto rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-400">
              Connected
            </span>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4 md:p-5">
            {messages.length === 0 && !loading && !historyLoading && (
              <div className="flex flex-1 flex-col items-center justify-center gap-4 py-8 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/10">
                  <Sparkles size={22} className="text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-300">Ask anything about your finances</p>
                  <p className="mt-1 text-xs text-zinc-600">
                    Spending totals, category breakdowns, subscriptions, and more
                  </p>
                </div>
                <div className="flex max-w-lg flex-wrap justify-center gap-2">
                  {EXAMPLE_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => void sendMessage(prompt)}
                      className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:border-zinc-700 hover:text-zinc-200"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {historyLoading && messages.length === 0 && (
              <div className="flex flex-1 items-center justify-center gap-2 text-sm text-zinc-500">
                <Loader2 size={16} className="animate-spin" />
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
                />
              ),
            )}

            {loading && messages[messages.length - 1]?.role !== "assistant" && (
              <AgentBubble content="" streaming />
            )}

            {error && (
              <p className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-2 text-sm text-red-400">
                {error}
              </p>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-zinc-800 p-4">
            <div className="flex items-end gap-2 rounded-xl border border-zinc-700 bg-zinc-800 px-3 py-2 focus-within:border-indigo-500/50">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about your finances…"
                rows={1}
                disabled={loading}
                className="max-h-32 min-h-[2.25rem] flex-1 resize-none bg-transparent py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none disabled:opacity-50"
              />
              {loading ? (
                <button
                  type="button"
                  onClick={handleStop}
                  aria-label="Stop generating"
                  className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200"
                >
                  <StopCircle size={18} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => void sendMessage()}
                  disabled={!input.trim()}
                  aria-label="Send message"
                  className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white transition-colors hover:bg-indigo-500 disabled:opacity-40"
                >
                  <Send size={15} />
                </button>
              )}
            </div>
            <p className="mt-2 text-center text-[10px] text-zinc-600">
              Enter to send · Shift+Enter for new line · Chats saved to your account
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-sm text-white sm:max-w-[70%]">
        {text}
      </div>
    </div>
  );
}

function AgentBubble({
  content,
  citations,
  streaming,
}: {
  content: string;
  citations?: TransactionCitation[];
  streaming?: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20">
        <BrainCircuit size={13} className="text-indigo-400" />
      </div>
      <div className="max-w-[90%] rounded-2xl rounded-tl-sm border border-zinc-800 bg-zinc-950 px-4 py-3 sm:max-w-[80%]">
        {streaming && !content ? (
          <span className="flex items-center gap-2 text-sm text-zinc-500">
            <Loader2 size={14} className="animate-spin" />
            Working on it…
          </span>
        ) : (
          <>
            <p className="whitespace-pre-wrap text-sm text-zinc-300">{content}</p>
            {citations && citations.length > 0 && (
              <div className="mt-3 border-t border-zinc-800 pt-3">
                <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-zinc-600">
                  Based on transactions
                </p>
                <ul className="flex flex-col gap-1.5">
                  {citations.map((c) => (
                    <li key={c.id} className="text-xs text-zinc-500">
                      <span className="text-zinc-400">{c.date ?? "—"}</span>
                      {" · "}
                      {c.description ?? c.merchant}
                      {c.amount != null && (
                        <span className={c.amount < 0 ? " text-rose-400" : " text-emerald-400"}>
                          {" "}
                          {c.amount < 0 ? "-" : "+"}${Math.abs(c.amount).toFixed(2)}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
