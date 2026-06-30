"use client";

import {
  Download,
  Lock,
  Palette,
  Shield,
  User,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import BankConnectPanel from "@/components/BankConnectPanel";
import ThemeToggle from "@/components/ThemeToggle";
import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import { exportToCsv } from "@/lib/utils";

export default function SettingsPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [profile, setProfile] = useState<{ email: string; name: string } | null>(null);
  const [dataCounts, setDataCounts] = useState({ accounts: 0, transactions: 0 });
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const fetchAll = useCallback(async () => {
    const [accounts, txList] = await Promise.all([
      api.getAccounts().catch(() => []),
      api.getTransactions({ limit: 1 }).catch(() => ({ total: 0, items: [] })),
    ]);

    let prof: { email: string; name: string } | null = null;
    if (isSupabaseConfigured()) {
      try {
        const u = await api.getMe();
        prof = { email: u.email, name: u.name };
      } catch {
        prof = null;
      }
    }

    return {
      profile: prof,
      accounts: accounts.length,
      transactions: txList.total,
    };
  }, []);

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    fetchAll()
      .then((data) => {
        if (!active) return;
        setProfile(data.profile);
        setDataCounts({ accounts: data.accounts, transactions: data.transactions });
        setLoading(false);
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [authReady, fetchAll]);

  const handleExportAll = async () => {
    setExporting(true);
    try {
      const txs = await api.getAllTransactions("2000-01-01", new Date().toISOString().slice(0, 10));
      exportToCsv("finsight-transactions.csv", [
        ["Date", "Description", "Amount", "Category", "Merchant", "Account"],
        ...txs.map((t) => [
          t.transaction_date,
          t.description,
          String(t.amount),
          t.category,
          t.merchant ?? "",
          t.account_id,
        ]),
      ]);
      toast(`Exported ${txs.length} transactions`);
    } catch {
      toast("Export failed", "error");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="page-container max-w-3xl">
      <PageHeader
        eyebrow="Preferences"
        title="Settings"
        subtitle="Your account, connected banks, and data."
      />

      <section className="panel settings-card stagger-item" style={{ "--stagger": 1 } as CSSProperties}>
        <div className="mb-4 flex items-center gap-2">
          <User size={16} className="text-[var(--accent)]" />
          <h2 className="section-title">Profile</h2>
        </div>
        {loading ? (
          <div className="h-12 shimmer rounded-xl" />
        ) : profile ? (
          <div className="settings-row border-0 pt-0">
            <div>
              <p className="text-sm font-medium text-[var(--foreground)]">{profile.name}</p>
              <p className="mt-0.5 text-sm text-[var(--muted)]">{profile.email}</p>
            </div>
            <span className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
              Active
            </span>
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">
            Sign in with Google to secure your financial data.
          </p>
        )}
      </section>

      <div className="stagger-item" style={{ "--stagger": 2 } as CSSProperties}>
        <BankConnectPanel />
      </div>

      <div className="settings-grid settings-grid--2">
        <section className="panel settings-card stagger-item" style={{ "--stagger": 3 } as CSSProperties}>
          <div className="mb-4 flex items-center gap-2">
            <Palette size={16} className="text-[var(--accent)]" />
            <h2 className="section-title">Appearance</h2>
          </div>
          <div className="settings-row border-0 pt-0">
            <div>
              <p className="text-sm font-medium text-[var(--foreground)]">Theme</p>
              <p className="mt-0.5 text-xs text-[var(--muted)]">Dark or light</p>
            </div>
            <ThemeToggle />
          </div>
        </section>

        <section className="panel settings-card stagger-item" style={{ "--stagger": 4 } as CSSProperties}>
          <div className="mb-4 flex items-center gap-2">
            <Shield size={16} className="text-[var(--accent)]" />
            <h2 className="section-title">Your data</h2>
          </div>
          <div className="space-y-3">
            <DataRow label="Linked accounts" value={loading ? "—" : String(dataCounts.accounts)} />
            <DataRow
              label="Transactions"
              value={loading ? "—" : dataCounts.transactions.toLocaleString()}
            />
          </div>
        </section>
      </div>

      <section className="panel settings-card stagger-item" style={{ "--stagger": 5 } as CSSProperties}>
        <div className="mb-4 flex items-center gap-2">
          <Lock size={16} className="text-[var(--accent)]" />
          <h2 className="section-title">Privacy</h2>
        </div>
        <p className="mb-4 text-sm leading-relaxed text-[var(--muted)]">
          Only you can see your transactions and chat history. Download a full copy anytime.
        </p>
        <button
          type="button"
          onClick={() => void handleExportAll()}
          disabled={exporting}
          className="btn-ghost inline-flex items-center gap-2 px-4 py-2.5 text-sm disabled:opacity-50"
        >
          <Download size={15} className={exporting ? "animate-pulse" : ""} />
          {exporting ? "Exporting…" : "Download transactions (CSV)"}
        </button>
        <Link href="/privacy" className="link-accent mt-4 inline-block text-sm">
          Read our privacy policy →
        </Link>
      </section>
    </div>
  );
}

function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 text-sm">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="font-medium tabular-nums text-[var(--foreground)]">{value}</span>
    </div>
  );
}
