"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api";
import {
  getPendingSessionIds,
  getSessionState,
  sendChatMessage,
  stopChatStream,
  subscribe,
  type SessionChatState,
} from "@/lib/chat-stream-manager";
import type { ChatSessionSummary } from "@/lib/types";

const SESSIONS_TTL_MS = 30_000;

type ChatStreamContextValue = {
  version: number;
  sessions: ChatSessionSummary[];
  sessionsLoading: boolean;
  getSessionState: (sessionId: string) => SessionChatState | undefined;
  pendingSessionIds: string[];
  refreshSessions: (force?: boolean) => Promise<ChatSessionSummary[]>;
  invalidateSessions: () => void;
  sendMessage: (
    message: string,
    options?: {
      sessionId?: string;
      newSession?: boolean;
      priorMessages?: import("@/lib/types").ChatMessage[];
    },
  ) => Promise<string>;
  stopSession: (sessionId: string) => void;
};

const ChatStreamContext = createContext<ChatStreamContextValue | null>(null);

export function ChatStreamProvider({ children }: { children: ReactNode }) {
  const [version, setVersion] = useState(0);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsFetchedAt, setSessionsFetchedAt] = useState(0);

  useEffect(() => subscribe(() => setVersion((v) => v + 1)), []);

  const invalidateSessions = useCallback(() => {
    setSessionsFetchedAt(0);
  }, []);

  const refreshSessions = useCallback(
    async (force = false) => {
      const fresh = force || Date.now() - sessionsFetchedAt >= SESSIONS_TTL_MS;
      if (!fresh && sessions.length > 0) {
        return sessions;
      }

      setSessionsLoading(true);
      try {
        const rows = await api.listChatSessions();
        setSessions(rows);
        setSessionsFetchedAt(Date.now());
        return rows;
      } catch {
        return sessions;
      } finally {
        setSessionsLoading(false);
      }
    },
    [sessions, sessionsFetchedAt],
  );

  const sendMessage = useCallback(
    async (
      message: string,
      options?: {
        sessionId?: string;
        newSession?: boolean;
        priorMessages?: import("@/lib/types").ChatMessage[];
      },
    ) => {
      const streamKey = await sendChatMessage(message, options);
      invalidateSessions();
      void refreshSessions(true);
      return streamKey;
    },
    [invalidateSessions, refreshSessions],
  );

  const stopSession = useCallback((sessionId: string) => {
    stopChatStream(sessionId);
  }, []);

  const value = useMemo(
    () => ({
      version,
      sessions,
      sessionsLoading,
      getSessionState,
      pendingSessionIds: getPendingSessionIds(),
      refreshSessions,
      invalidateSessions,
      sendMessage,
      stopSession,
    }),
    [version, sessions, sessionsLoading, refreshSessions, invalidateSessions, sendMessage, stopSession],
  );

  return <ChatStreamContext.Provider value={value}>{children}</ChatStreamContext.Provider>;
}

export function useChatStream() {
  const ctx = useContext(ChatStreamContext);
  if (!ctx) {
    throw new Error("useChatStream must be used within ChatStreamProvider");
  }
  return ctx;
}
