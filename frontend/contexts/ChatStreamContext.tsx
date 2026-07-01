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

import {
  getPendingSessionIds,
  getSessionState,
  sendChatMessage,
  stopChatStream,
  subscribe,
  type SessionChatState,
} from "@/lib/chat-stream-manager";

type ChatStreamContextValue = {
  version: number;
  getSessionState: (sessionId: string) => SessionChatState | undefined;
  pendingSessionIds: string[];
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

  useEffect(() => subscribe(() => setVersion((v) => v + 1)), []);

  const sendMessage = useCallback(
    (message: string, options?: { sessionId?: string; newSession?: boolean }) =>
      sendChatMessage(message, options),
    [],
  );

  const stopSession = useCallback((sessionId: string) => {
    stopChatStream(sessionId);
  }, []);

  const value = useMemo(
    () => ({
      version,
      getSessionState,
      pendingSessionIds: getPendingSessionIds(),
      sendMessage,
      stopSession,
    }),
    [version, sendMessage, stopSession],
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
