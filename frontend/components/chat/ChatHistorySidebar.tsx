"use client";

import {
  MessageSquare,
  MessageSquarePlus,
  MoreHorizontal,
  Pencil,
  Pin,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";

import type { ChatSessionSummary } from "@/lib/types";

function formatSessionDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) {
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return d.toLocaleDateString([], { weekday: "short" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function ChatHistorySidebar({
  sessions,
  sessionId,
  loading,
  renamingId,
  renameValue,
  onNewChat,
  onSelect,
  onRenameStart,
  onRenameChange,
  onRenameCommit,
  onRenameCancel,
  onTogglePin,
  onDelete,
}: {
  sessions: ChatSessionSummary[];
  sessionId: string;
  loading: boolean;
  renamingId: string | null;
  renameValue: string;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onRenameStart: (s: ChatSessionSummary) => void;
  onRenameChange: (v: string) => void;
  onRenameCommit: (id: string) => void;
  onRenameCancel: () => void;
  onTogglePin: (s: ChatSessionSummary) => void;
  onDelete: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [menuId, setMenuId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((s) => s.title.toLowerCase().includes(q));
  }, [sessions, query]);

  const pinned = filtered.filter((s) => s.pinned);
  const recent = filtered.filter((s) => !s.pinned);

  return (
    <aside className="chat-sidebar">
      <button
        type="button"
        onClick={onNewChat}
        className="btn-primary flex w-full items-center justify-center gap-2 px-4 py-2.5 text-sm"
      >
        <MessageSquarePlus size={15} />
        New chat
      </button>

      <div className="chat-history-panel panel flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl">
        <div className="border-b border-[var(--border)] px-3 py-3">
          <div className="chat-search-wrap">
            <Search size={15} className="chat-search-icon" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search conversations"
              className="input-field chat-search-input"
              aria-label="Search conversations"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-2 top-1/2 z-10 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
                aria-label="Clear search"
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-2">
          {loading ? (
            <div className="space-y-2 p-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-[4.25rem] shimmer rounded-xl" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center gap-3 px-4 py-10 text-center">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
                <MessageSquare size={18} className="text-[var(--accent)]" />
              </div>
              <p className="text-xs leading-relaxed text-[var(--muted)]">
                {query
                  ? "No conversations match your search."
                  : "Conversations you start will appear here."}
              </p>
            </div>
          ) : (
            <>
              {pinned.length > 0 && (
                <SessionGroup label="Pinned">
                  {pinned.map((s) => (
                    <SessionCard
                      key={s.id}
                      session={s}
                      active={sessionId === s.id}
                      renaming={renamingId === s.id}
                      renameValue={renameValue}
                      menuOpen={menuId === s.id}
                      onSelect={() => onSelect(s.id)}
                      onRenameChange={onRenameChange}
                      onRenameCommit={() => onRenameCommit(s.id)}
                      onRenameCancel={onRenameCancel}
                      onMenuToggle={() => setMenuId(menuId === s.id ? null : s.id)}
                      onPin={() => {
                        onTogglePin(s);
                        setMenuId(null);
                      }}
                      onRename={() => {
                        onRenameStart(s);
                        setMenuId(null);
                      }}
                      onDelete={() => {
                        onDelete(s.id);
                        setMenuId(null);
                      }}
                    />
                  ))}
                </SessionGroup>
              )}
              {recent.length > 0 && (
                <SessionGroup label={pinned.length > 0 ? "Recent" : "All chats"}>
                  {recent.map((s) => (
                    <SessionCard
                      key={s.id}
                      session={s}
                      active={sessionId === s.id}
                      renaming={renamingId === s.id}
                      renameValue={renameValue}
                      menuOpen={menuId === s.id}
                      onSelect={() => onSelect(s.id)}
                      onRenameChange={onRenameChange}
                      onRenameCommit={() => onRenameCommit(s.id)}
                      onRenameCancel={onRenameCancel}
                      onMenuToggle={() => setMenuId(menuId === s.id ? null : s.id)}
                      onPin={() => {
                        onTogglePin(s);
                        setMenuId(null);
                      }}
                      onRename={() => {
                        onRenameStart(s);
                        setMenuId(null);
                      }}
                      onDelete={() => {
                        onDelete(s.id);
                        setMenuId(null);
                      }}
                    />
                  ))}
                </SessionGroup>
              )}
            </>
          )}
        </div>
      </div>
    </aside>
  );
}

function SessionGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted)]">
        {label}
      </p>
      <ul className="flex flex-col gap-1">{children}</ul>
    </div>
  );
}

function SessionCard({
  session,
  active,
  renaming,
  renameValue,
  menuOpen,
  onSelect,
  onRenameChange,
  onRenameCommit,
  onRenameCancel,
  onMenuToggle,
  onPin,
  onRename,
  onDelete,
}: {
  session: ChatSessionSummary;
  active: boolean;
  renaming: boolean;
  renameValue: string;
  menuOpen: boolean;
  onSelect: () => void;
  onRenameChange: (v: string) => void;
  onRenameCommit: () => void;
  onRenameCancel: () => void;
  onMenuToggle: () => void;
  onPin: () => void;
  onRename: () => void;
  onDelete: () => void;
}) {
  return (
    <li>
      <div
        className={[
          "chat-session-card group",
          active && "chat-session-card--active",
        ].join(" ")}
      >
        {active && <span className="chat-session-indicator" aria-hidden />}

        {renaming ? (
          <input
            autoFocus
            value={renameValue}
            onChange={(e) => onRenameChange(e.target.value)}
            onBlur={onRenameCommit}
            onKeyDown={(e) => {
              if (e.key === "Enter") onRenameCommit();
              if (e.key === "Escape") onRenameCancel();
            }}
            className="input-field w-full py-1.5 text-xs"
          />
        ) : (
          <div className="flex items-start gap-1">
            <button type="button" onClick={onSelect} className="min-w-0 flex-1 text-left">
              <div className="flex items-start gap-1.5">
                {session.pinned && (
                  <Pin size={11} className="mt-1 shrink-0 text-amber-400" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="line-clamp-2 text-sm font-medium leading-snug text-[var(--foreground)]">
                    {session.title}
                  </p>
                  <div className="mt-1 flex items-center gap-1.5 text-[10px] text-[var(--muted)]">
                    <span className="shrink-0">{formatSessionDate(session.updated_at)}</span>
                    {session.message_count > 0 && (
                      <>
                        <span className="opacity-40">·</span>
                        <span className="truncate">{session.message_count} msgs</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </button>

            <div className="relative shrink-0">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onMenuToggle();
                }}
                aria-label="Conversation options"
                className={[
                  "flex h-7 w-7 items-center justify-center rounded-lg transition-colors",
                  menuOpen
                    ? "bg-[var(--surface-elevated)] text-[var(--foreground)]"
                    : "text-[var(--muted)] opacity-70 hover:bg-[var(--surface-elevated)] hover:text-[var(--foreground)] md:opacity-0 md:group-hover:opacity-100",
                ].join(" ")}
              >
                <MoreHorizontal size={14} />
              </button>

              {menuOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={onMenuToggle} aria-hidden />
                  <div className="absolute right-0 z-20 mt-1 min-w-[9rem] overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-elevated)] py-1 shadow-lg">
                    <MenuItem icon={<Pin size={13} />} onClick={onPin}>
                      {session.pinned ? "Unpin" : "Pin"}
                    </MenuItem>
                    <MenuItem icon={<Pencil size={13} />} onClick={onRename}>
                      Rename
                    </MenuItem>
                    <MenuItem icon={<Trash2 size={13} />} onClick={onDelete} danger>
                      Delete
                    </MenuItem>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </li>
  );
}

function MenuItem({
  children,
  icon,
  onClick,
  danger,
}: {
  children: React.ReactNode;
  icon: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors",
        danger
          ? "text-rose-400 hover:bg-rose-500/10"
          : "text-[var(--foreground)] hover:bg-[var(--surface)]",
      ].join(" ")}
    >
      {icon}
      {children}
    </button>
  );
}
