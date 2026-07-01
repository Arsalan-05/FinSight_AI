/**
 * Runs chat SSE streams outside any page component so replies continue when
 * navigating away and multiple sessions can stream concurrently.
 */

import { api } from "@/lib/api";
import type { ChatMessage, TransactionCitation } from "@/lib/types";

export const SESSION_KEY = "finsight_chat_session";
const DRAFT_PREFIX = "finsight_chat_draft_";
const DRAFT_MAX_AGE_MS = 30 * 60 * 1000;

export type SessionChatState = {
  sessionId: string;
  messages: ChatMessage[];
  loading: boolean;
  agentStatus: string | null;
  error: string | null;
};

type Listener = () => void;

const states = new Map<string, SessionChatState>();
const abortControllers = new Map<string, AbortController>();
const listeners = new Set<Listener>();
/** Provisional stream key → server session id after first SSE session event */
export const sessionMigrations = new Map<string, string>();

function draftKey(sessionId: string) {
  return `${DRAFT_PREFIX}${sessionId}`;
}

function newMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return { id: crypto.randomUUID(), role, content };
}

function notify() {
  listeners.forEach((cb) => cb());
}

function saveDraft(state: SessionChatState) {
  if (!state.sessionId) return;
  try {
    sessionStorage.setItem(
      draftKey(state.sessionId),
      JSON.stringify({
        sessionId: state.sessionId,
        messages: state.messages,
        loading: state.loading,
        at: Date.now(),
      }),
    );
  } catch {
    // ignore quota
  }
}

export function loadSessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    return localStorage.getItem(SESSION_KEY) ?? "";
  } catch {
    return "";
  }
}

export function saveSessionId(id: string) {
  if (!id) return;
  localStorage.setItem(SESSION_KEY, id);
}

export function clearSessionId() {
  localStorage.removeItem(SESSION_KEY);
}

export function loadChatDraft(sessionId: string): SessionChatState | null {
  if (!sessionId) return null;
  try {
    const raw = sessionStorage.getItem(draftKey(sessionId));
    if (!raw) return null;
    const draft = JSON.parse(raw) as {
      sessionId: string;
      messages: ChatMessage[];
      loading?: boolean;
      at: number;
    };
    if (Date.now() - draft.at > DRAFT_MAX_AGE_MS) {
      sessionStorage.removeItem(draftKey(sessionId));
      return null;
    }
    return {
      sessionId: draft.sessionId,
      messages: draft.messages,
      loading: Boolean(draft.loading),
      agentStatus: null,
      error: null,
    };
  } catch {
    return null;
  }
}

export function clearChatDraft(sessionId: string) {
  if (!sessionId) return;
  try {
    sessionStorage.removeItem(draftKey(sessionId));
  } catch {
    // ignore
  }
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSessionState(sessionId: string): SessionChatState | undefined {
  return states.get(sessionId);
}

export function getStreamingSessionIds(): string[] {
  return [...states.entries()].filter(([, s]) => s.loading).map(([id]) => id);
}

export function isSessionLoading(sessionId: string): boolean {
  return Boolean(states.get(sessionId)?.loading);
}

function setState(sessionId: string, patch: Partial<SessionChatState>) {
  const prev = states.get(sessionId);
  if (!prev) return;
  const next = { ...prev, ...patch };
  states.set(sessionId, next);
  saveDraft(next);
  notify();
}

function migrateState(fromId: string, toId: string) {
  const prev = states.get(fromId);
  if (!prev) return toId;
  states.delete(fromId);
  const next = { ...prev, sessionId: toId };
  states.set(toId, next);
  if (fromId.startsWith("new:")) {
    sessionMigrations.set(fromId, toId);
    abortControllers.set(toId, abortControllers.get(fromId)!);
    abortControllers.delete(fromId);
  }
  saveDraft(next);
  notify();
  return toId;
}

const AGENT_STATUS = [
  "Reviewing your accounts…",
  "Querying transaction history…",
  "Running spending analysis…",
  "Searching for current rates…",
  "Synthesizing insights…",
];

export function stopChatStream(sessionId: string) {
  abortControllers.get(sessionId)?.abort();
  abortControllers.delete(sessionId);
  const state = states.get(sessionId);
  if (state?.loading) {
    setState(sessionId, { loading: false, agentStatus: null });
  }
}

export async function sendChatMessage(
  message: string,
  options?: {
    sessionId?: string;
    newSession?: boolean;
    priorMessages?: ChatMessage[];
  },
): Promise<string> {
  const existingId = options?.newSession ? "" : (options?.sessionId ?? "");
  const streamKey = existingId || `new:${crypto.randomUUID()}`;

  if (states.get(streamKey)?.loading) {
    return streamKey;
  }

  const userMsg = newMessage("user", message);
  const assistantId = crypto.randomUUID();
  const prior =
    options?.priorMessages ??
    (existingId ? states.get(existingId)?.messages : undefined) ??
    [];

  const initial: SessionChatState = {
    sessionId: existingId,
    messages: [
      ...prior,
      userMsg,
      { id: assistantId, role: "assistant", content: "", citations: [] },
    ],
    loading: true,
    agentStatus: AGENT_STATUS[0],
    error: null,
  };
  states.set(streamKey, initial);
  saveDraft(initial);
  notify();

  const controller = new AbortController();
  abortControllers.set(streamKey, controller);

  let activeKey = streamKey;
  let activeSessionId = existingId;
  let statusIdx = 0;
  const fallbackTimer = setInterval(() => {
    statusIdx = (statusIdx + 1) % AGENT_STATUS.length;
    const st = states.get(activeKey);
    if (st?.loading) {
      setState(activeKey, { agentStatus: AGENT_STATUS[statusIdx] });
    }
  }, 2400);

  void (async () => {
    try {
      let reply = "";
      let citations: TransactionCitation[] = [];

      for await (const event of api.chatStream(
        message,
        existingId || undefined,
        controller.signal,
      )) {
        if (event.type === "session") {
          activeSessionId = event.session_id;
          if (activeKey !== activeSessionId) {
            activeKey = migrateState(activeKey, activeSessionId);
          }
          saveSessionId(activeSessionId);
        } else if (event.type === "status") {
          setState(activeKey, { agentStatus: event.detail || event.phase });
        } else if (event.type === "token") {
          reply += event.content;
          const st = states.get(activeKey);
          if (st) {
            setState(activeKey, {
              messages: st.messages.map((m) =>
                m.id === assistantId ? { ...m, content: reply } : m,
              ),
            });
          }
        } else if (event.type === "done") {
          reply = event.content;
          citations = event.citations ?? [];
          activeSessionId = event.session_id;
          if (activeKey !== activeSessionId) {
            activeKey = migrateState(activeKey, activeSessionId);
          }
          const st = states.get(activeKey);
          if (st) {
            setState(activeKey, {
              sessionId: activeSessionId,
              messages: st.messages.map((m) =>
                m.id === assistantId ? { ...m, content: reply, citations } : m,
              ),
              loading: false,
              agentStatus: null,
              error: null,
            });
          }
          saveSessionId(activeSessionId);
          clearChatDraft(activeSessionId);
        } else if (event.type === "error") {
          throw new Error(event.message);
        }
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        const msg = e instanceof Error ? e.message : "Chat failed";
        const st = states.get(activeKey);
        if (st) {
          const assistant = st.messages.find((m) => m.id === assistantId);
          setState(activeKey, {
            loading: false,
            agentStatus: null,
            error: msg,
            messages:
              assistant?.content?.trim()
                ? st.messages
                : st.messages.filter((m) => m.id !== assistantId),
          });
        }
      } else {
        setState(activeKey, { loading: false, agentStatus: null });
      }
    } finally {
      clearInterval(fallbackTimer);
      abortControllers.delete(activeKey);
      const st = states.get(activeKey);
      if (st?.loading) {
        setState(activeKey, { loading: false, agentStatus: null });
      }
      notify();
    }
  })();

  return streamKey;
}

export function hydrateSessionState(
  sessionId: string,
  messages: ChatMessage[],
): SessionChatState {
  const live = states.get(sessionId);
  if (live?.loading) {
    return live;
  }
  const draft = loadChatDraft(sessionId);
  if (draft && (draft.loading || draft.messages.length > messages.length)) {
    states.set(sessionId, draft);
    return draft;
  }
  const state: SessionChatState = {
    sessionId,
    messages,
    loading: false,
    agentStatus: null,
    error: null,
  };
  states.set(sessionId, state);
  return state;
}
