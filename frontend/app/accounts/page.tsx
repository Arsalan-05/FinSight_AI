"use client";

import { Building2, Plus, RefreshCw, User2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import type { Account, User } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export default function AccountsPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [users, setUsers] = useState<User[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [authUser, setAuthUser] = useState<User | null>(null);
  const [showNewUser, setShowNewUser] = useState(false);
  const [showNewAccount, setShowNewAccount] = useState(false);

  const fetchAll = useCallback(() => {
    return api.getMe().then((me) => {
      setAuthUser(me);
      return api.getAccounts().then((accs) => ({ users: [me], accounts: accs }));
    });
  }, []);

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    fetchAll()
      .then(({ users: u, accounts: a }) => {
        if (!active) return;
        setUsers(u);
        setAccounts(a);
        setLoading(false);
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [authReady, fetchAll]);

  const load = useCallback(() => {
    setLoading(true);
    fetchAll().then(({ users: u, accounts: a }) => {
      setUsers(u);
      setAccounts(a);
      setLoading(false);
    });
  }, [fetchAll]);

  const accountsByUser = users.map((u) => ({
    user: u,
    accounts: accounts.filter((a) => a.user_id === u.id),
  }));

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Finance"
        title="Accounts"
        subtitle={`${users.length} user${users.length !== 1 ? "s" : ""} · ${accounts.length} account${accounts.length !== 1 ? "s" : ""}`}
        actions={
          <>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="btn-ghost flex h-9 w-9 items-center justify-center rounded-xl disabled:opacity-40"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              type="button"
              onClick={() => setShowNewAccount(true)}
              disabled={users.length === 0}
              className="btn-ghost flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium disabled:opacity-40"
            >
              <Building2 size={13} />
              New Account
            </button>
            {!authUser && (
              <button
                type="button"
                onClick={() => setShowNewUser(true)}
                className="btn-primary flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium"
              >
                <Plus size={13} />
                New User
              </button>
            )}
          </>
        }
      />

      {/* No data hint */}
      {!loading && users.length === 0 && (
        <div className="card flex flex-col items-center gap-4 border-dashed py-16 text-center">
          <User2 size={32} className="text-[var(--muted)]" />
          <div>
            <p className="text-sm font-medium text-[var(--foreground)]">No profile yet</p>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {authUser
                ? "Add your first financial account to get started."
                : "Sign in or create a user, then add financial accounts."}
            </p>
          </div>
          {!authUser && (
            <button
              type="button"
              onClick={() => setShowNewUser(true)}
              className="btn-primary rounded-xl px-4 py-2 text-sm font-medium"
            >
              Create User
            </button>
          )}
        </div>
      )}

      {/* User + accounts grid */}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-40 shimmer rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {accountsByUser.map(({ user, accounts: userAccounts }) => (
            <section key={user.id}>
              {/* User header */}
              <div className="mb-3 flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-500/20 text-sm font-semibold text-indigo-300">
                  {user.name[0]?.toUpperCase()}
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-200">{user.name}</p>
                  <p className="text-xs text-zinc-500">{user.email}</p>
                </div>
                <span className="ml-auto text-xs text-zinc-600">
                  Since {formatDate(user.created_at.slice(0, 10))}
                </span>
              </div>

              {/* Accounts */}
              {userAccounts.length === 0 ? (
                <div className="rounded-xl border border-dashed border-zinc-800 py-8 text-center">
                  <p className="text-sm text-zinc-600">No accounts for this user.</p>
                  <button
                    onClick={() => setShowNewAccount(true)}
                    className="mt-3 text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    + Add account
                  </button>
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {userAccounts.map((acc) => (
                    <AccountCard key={acc.id} account={acc} />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}

      {/* Modals */}
      {showNewUser && (
        <NewUserModal
          onClose={() => setShowNewUser(false)}
          onCreated={() => { setShowNewUser(false); toast("User created"); void load(); }}
        />
      )}
      {showNewAccount && (
        <NewAccountModal
          users={users}
          onClose={() => setShowNewAccount(false)}
          onCreated={() => { setShowNewAccount(false); toast("Account created"); void load(); }}
        />
      )}
    </div>
  );
}

// ── Account card ──────────────────────────────────────────────────────────────

function AccountCard({ account }: { account: Account }) {
  const typeColors: Record<string, string> = {
    checking: "text-sky-400 bg-sky-500/10",
    savings: "text-emerald-400 bg-emerald-500/10",
    credit: "text-rose-400 bg-rose-500/10",
  };
  const typeStyle = typeColors[account.account_type] ?? "text-zinc-400 bg-zinc-800";

  return (
    <div className="flex flex-col gap-3 panel rounded-2xl p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <Building2 size={15} className="text-zinc-500" />
          <span className="text-sm font-medium text-zinc-200">{account.name}</span>
        </div>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${typeStyle}`}>
          {account.account_type}
        </span>
      </div>
      <p className="text-xs text-zinc-500">{account.institution}</p>
      <p className="text-xs text-zinc-700">
        Added {formatDate(account.created_at.slice(0, 10))}
      </p>
      <p className="truncate text-[10px] font-mono text-zinc-800">{account.id}</p>
    </div>
  );
}

// ── New User Modal ────────────────────────────────────────────────────────────

function NewUserModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createUser({ name, email });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="New User" onClose={onClose}>
      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        <Field label="Full Name">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputCls}
            placeholder="Arsalan Amir Ali"
            required
          />
        </Field>
        <Field label="Email">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputCls}
            placeholder="arsalan@example.com"
            required
          />
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className={cancelBtnCls}>Cancel</button>
          <button type="submit" disabled={saving} className={primaryBtnCls}>
            {saving ? "Saving…" : "Create User"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── New Account Modal ─────────────────────────────────────────────────────────

function NewAccountModal({
  users,
  onClose,
  onCreated,
}: {
  users: User[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    user_id: users[0]?.id ?? "",
    name: "",
    institution: "",
    account_type: "checking",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await api.createAccount(form);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create account");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="New Account" onClose={onClose}>
      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-400">{error}</p>}
        <Field label="User">
          <select
            value={form.user_id}
            onChange={(e) => setForm({ ...form, user_id: e.target.value })}
            className={inputCls}
          >
            {users.map((u) => (
              <option key={u.id} value={u.id}>{u.name} — {u.email}</option>
            ))}
          </select>
        </Field>
        <Field label="Account Name">
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className={inputCls}
            placeholder="e.g. Main Chequing"
            required
          />
        </Field>
        <Field label="Institution">
          <input
            type="text"
            value={form.institution}
            onChange={(e) => setForm({ ...form, institution: e.target.value })}
            className={inputCls}
            placeholder="e.g. TD Bank"
            required
          />
        </Field>
        <Field label="Account Type">
          <select
            value={form.account_type}
            onChange={(e) => setForm({ ...form, account_type: e.target.value })}
            className={inputCls}
          >
            <option value="checking">Checking</option>
            <option value="savings">Savings</option>
            <option value="credit">Credit</option>
          </select>
        </Field>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className={cancelBtnCls}>Cancel</button>
          <button type="submit" disabled={saving} className={primaryBtnCls}>
            {saving ? "Saving…" : "Create Account"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── Shared ────────────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: {
  title: string; onClose: () => void; children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-zinc-400">{label}</label>
      {children}
    </div>
  );
}

const inputCls =
  "w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500";
const primaryBtnCls =
  "rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:opacity-40";
const cancelBtnCls =
  "rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200";
