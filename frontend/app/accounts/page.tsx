"use client";

import { Building2, ChevronRight, CreditCard, Landmark, Plus, Wallet, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import type { Account, User } from "@/lib/types";
import { formatDate } from "@/lib/utils";

const INSTITUTION_LABELS: Record<string, string> = {
  RBC: "Royal Bank of Canada",
  TD: "TD Canada Trust",
  BMO: "BMO",
  CIBC: "CIBC",
  Scotiabank: "Scotiabank",
};

function accountIcon(type: string) {
  if (type === "credit") return CreditCard;
  if (type === "savings") return Wallet;
  return Landmark;
}

export default function AccountsPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const supabase = isSupabaseConfigured();
  const [authUser, setAuthUser] = useState<User | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewAccount, setShowNewAccount] = useState(false);

  const fetchAll = useCallback(() => {
    return api.getMe().then((me) => {
      setAuthUser(me);
      return api.getAccounts().then((accs) => accs);
    });
  }, []);

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    fetchAll()
      .then((accs) => {
        if (!active) return;
        setAccounts(accs);
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
    fetchAll().then((accs) => {
      setAccounts(accs);
      setLoading(false);
    });
  }, [fetchAll]);

  const subtitle =
    accounts.length === 0
      ? "Link accounts to track spending and power your finance agent"
      : `${accounts.length} linked account${accounts.length !== 1 ? "s" : ""}`;

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Banking"
        title="Accounts"
        subtitle={subtitle}
        actions={
          <button
            type="button"
            onClick={() => setShowNewAccount(true)}
            disabled={!authUser && !supabase}
            className="btn-primary flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium disabled:opacity-40"
          >
            <Plus size={13} />
            Add account
          </button>
        }
      />

      {!loading && !authUser && !supabase && (
        <div className="card flex flex-col items-center gap-4 border-dashed py-16 text-center">
          <Building2 size={32} className="text-[var(--muted)]" />
          <div>
            <p className="text-sm font-medium text-[var(--foreground)]">Sign in to manage accounts</p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Connect your profile, then add chequing, savings, or credit accounts.
            </p>
          </div>
        </div>
      )}

      {!loading && authUser && accounts.length === 0 && (
        <div className="panel flex flex-col items-center gap-4 rounded-2xl border-dashed py-14 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--accent-soft)]">
            <Landmark size={22} className="text-[var(--accent)]" />
          </div>
          <div>
            <p className="text-base font-medium text-[var(--foreground)]">No accounts yet</p>
            <p className="mt-1 max-w-sm text-sm text-[var(--muted)]">
              Add a manual account or connect your bank in Settings to start importing transactions.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowNewAccount(true)}
            className="btn-primary rounded-xl px-5 py-2.5 text-sm"
          >
            Add your first account
          </button>
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-44 shimmer rounded-2xl" />
          ))}
        </div>
      ) : (
        accounts.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {accounts.map((acc) => (
              <AccountCard key={acc.id} account={acc} />
            ))}
          </div>
        )
      )}

      {showNewAccount && authUser && (
        <NewAccountModal
          user={authUser}
          onClose={() => setShowNewAccount(false)}
          onCreated={() => {
            setShowNewAccount(false);
            toast("Account added");
            void load();
          }}
        />
      )}
    </div>
  );
}

function AccountCard({ account }: { account: Account }) {
  const Icon = accountIcon(account.account_type);
  const institution =
    INSTITUTION_LABELS[account.institution] ?? account.institution;

  const typeColors: Record<string, string> = {
    checking: "text-teal-300 bg-teal-500/15 border-teal-500/25",
    savings: "text-emerald-300 bg-emerald-500/15 border-emerald-500/25",
    credit: "text-rose-300 bg-rose-500/15 border-rose-500/25",
  };
  const typeStyle =
    typeColors[account.account_type] ??
    "text-[var(--foreground)] bg-[var(--surface)] border-[var(--border)]";

  return (
    <Link
      href={`/accounts/${account.id}`}
      className="panel group flex flex-col gap-4 rounded-2xl p-5 transition-colors hover:border-[var(--accent)]/40 hover:bg-[var(--accent-soft)]/20"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)]">
          <Icon size={20} className="text-[var(--accent)]" />
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${typeStyle}`}
        >
          {account.account_type}
        </span>
      </div>

      <div>
        <h3 className="text-base font-semibold text-[var(--foreground)]">{account.name}</h3>
        <p className="mt-1 text-sm text-[var(--muted)]">{institution}</p>
      </div>

      <p className="flex items-center justify-between text-xs text-[var(--muted)]">
        <span>Added {formatDate(account.created_at.slice(0, 10))}</span>
        <ChevronRight size={14} className="opacity-0 transition-opacity group-hover:opacity-100" />
      </p>
    </Link>
  );
}

function NewAccountModal({
  user,
  onClose,
  onCreated,
}: {
  user: User;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
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
      await api.createAccount({
        user_id: user.id,
        ...form,
      });
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add account");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Add account" onClose={onClose}>
      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
        {error && <p className="text-sm text-rose-400">{error}</p>}
        <Field label="Account name">
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="input-field"
            placeholder="e.g. Main Chequing"
            required
          />
        </Field>
        <Field label="Bank / institution">
          <input
            type="text"
            value={form.institution}
            onChange={(e) => setForm({ ...form, institution: e.target.value })}
            className="input-field"
            placeholder="e.g. TD, RBC, Scotiabank"
            required
          />
        </Field>
        <Field label="Account type">
          <select
            value={form.account_type}
            onChange={(e) => setForm({ ...form, account_type: e.target.value })}
            className="select-field w-full"
          >
            <option value="checking">Chequing</option>
            <option value="savings">Savings</option>
            <option value="credit">Credit card</option>
          </select>
        </Field>
        <ModalActions onClose={onClose} saving={saving} label="Add account" />
      </form>
    </Modal>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div className="modal-panel relative z-10">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-semibold text-[var(--foreground)]">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
          >
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
      <label className="text-xs font-medium text-[var(--muted)]">{label}</label>
      {children}
    </div>
  );
}

function ModalActions({
  onClose,
  saving,
  label,
}: {
  onClose: () => void;
  saving: boolean;
  label: string;
}) {
  return (
    <div className="flex justify-end gap-2 pt-1">
      <button type="button" onClick={onClose} className="btn-ghost px-4 py-2 text-sm">
        Cancel
      </button>
      <button type="submit" disabled={saving} className="btn-primary px-4 py-2 text-sm disabled:opacity-40">
        {saving ? "Saving…" : label}
      </button>
    </div>
  );
}
