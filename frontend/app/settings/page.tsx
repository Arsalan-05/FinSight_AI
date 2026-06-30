"use client";

import {
  AlertTriangle,
  Download,
  Lock,
  Palette,
  Shield,
  User,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import BankConnectPanel from "@/components/BankConnectPanel";
import ThemeToggle from "@/components/ThemeToggle";
import { ToggleSwitch } from "@/components/ui/ToggleSwitch";
import { PageHeader } from "@/components/ui/PageHeader";
import { useToast } from "@/contexts/ToastContext";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import type { AlertPreferences } from "@/lib/types";
import { exportToCsv } from "@/lib/utils";

const DEFAULT_ALERT_PREFS: AlertPreferences = {
  spend_alerts: true,
  email_digest: false,
};

export default function SettingsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [profile, setProfile] = useState<{ email: string; name: string } | null>(null);
  const [dataCounts, setDataCounts] = useState({ accounts: 0, transactions: 0 });
  const [alertPrefs, setAlertPrefs] = useState<AlertPreferences>(DEFAULT_ALERT_PREFS);
  const [prefsLoading, setPrefsLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportingJson, setExportingJson] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [sendingDigest, setSendingDigest] = useState(false);

  const fetchAll = useCallback(async () => {
    const [accounts, txList] = await Promise.all([
      api.getAccounts().catch(() => []),
      api.getTransactions({ limit: 1 }).catch(() => ({ total: 0, items: [] })),
    ]);

    let prof: { email: string; name: string } | null = null;
    let prefs = DEFAULT_ALERT_PREFS;

    if (isSupabaseConfigured()) {
      try {
        const u = await api.getMe();
        prof = { email: u.email, name: u.name };
      } catch {
        prof = null;
      }
      try {
        prefs = await api.getAlertPreferences();
      } catch {
        prefs = DEFAULT_ALERT_PREFS;
      }
    }

    return {
      profile: prof,
      prefs,
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
        setAlertPrefs(data.prefs);
        setDataCounts({ accounts: data.accounts, transactions: data.transactions });
        setLoading(false);
        setPrefsLoading(false);
      })
      .catch(() => {
        if (active) {
          setLoading(false);
          setPrefsLoading(false);
        }
      });
    return () => { active = false; };
  }, [authReady, fetchAll]);

  const handleExportCsv = async () => {
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

  const handleExportJson = async () => {
    setExportingJson(true);
    try {
      const data = await api.exportMyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "finsight-export.json";
      a.click();
      URL.revokeObjectURL(url);
      toast("Full data export downloaded");
    } catch {
      toast("Export failed", "error");
    } finally {
      setExportingJson(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!window.confirm("Permanently delete your account and all data? This cannot be undone.")) {
      return;
    }
    setDeleting(true);
    try {
      await api.deleteMyAccount();
      toast("Account deleted");
      router.push("/login");
    } catch {
      toast("Could not delete account", "error");
    } finally {
      setDeleting(false);
    }
  };

  const togglePref = async (key: keyof AlertPreferences, value: boolean) => {
    const previous = alertPrefs;
    setAlertPrefs((prev) => ({ ...prev, [key]: value }));
    try {
      const updated = await api.updateAlertPreferences({ [key]: value });
      setAlertPrefs(updated);
    } catch {
      setAlertPrefs(previous);
      toast("Could not save preferences", "error");
    }
  };

  const handleSendDigest = async () => {
    setSendingDigest(true);
    try {
      await api.sendDigest();
      toast("Weekly digest sent to your email");
    } catch {
      toast("Digest not sent — enable email digest and configure SMTP", "error");
    } finally {
      setSendingDigest(false);
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

      <section className="panel settings-card stagger-item" style={{ "--stagger": 3 } as CSSProperties}>
        <div className="mb-4 flex items-center gap-2">
          <Shield size={16} className="text-[var(--accent)]" />
          <h2 className="section-title">Alerts</h2>
        </div>
        {prefsLoading ? (
          <div className="h-16 shimmer rounded-xl" />
        ) : (
          <div className="divide-y divide-[var(--border)]">
            <PrefRow
              label="Spend alerts"
              desc="In-app notifications when you exceed a budget"
              checked={alertPrefs.spend_alerts}
              onChange={(v) => void togglePref("spend_alerts", v)}
            />
            <PrefRow
              label="Weekly email digest"
              desc="Monday summary of spending and alerts"
              checked={alertPrefs.email_digest}
              onChange={(v) => void togglePref("email_digest", v)}
            />
            {alertPrefs.email_digest && (
              <div className="pt-3">
                <button
                  type="button"
                  onClick={() => void handleSendDigest()}
                  disabled={sendingDigest}
                  className="btn-ghost inline-flex items-center gap-2 px-4 py-2.5 text-sm disabled:opacity-50"
                >
                  {sendingDigest ? "Sending…" : "Send test digest now"}
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      <div className="settings-grid settings-grid--2">
        <section className="panel settings-card stagger-item" style={{ "--stagger": 4 } as CSSProperties}>
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

        <section className="panel settings-card stagger-item" style={{ "--stagger": 5 } as CSSProperties}>
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

      <section className="panel settings-card stagger-item" style={{ "--stagger": 6 } as CSSProperties}>
        <div className="mb-4 flex items-center gap-2">
          <Lock size={16} className="text-[var(--accent)]" />
          <h2 className="section-title">Privacy</h2>
        </div>
        <p className="mb-4 text-sm leading-relaxed text-[var(--muted)]">
          Only you can see your transactions and chat history. Download a full copy anytime or
          permanently delete your account.
        </p>
        <div className="settings-actions">
          <button
            type="button"
            onClick={() => void handleExportCsv()}
            disabled={exporting}
            className="btn-ghost inline-flex items-center gap-2 px-4 py-2.5 text-sm disabled:opacity-50"
          >
            <Download size={15} className={exporting ? "animate-pulse" : ""} />
            {exporting ? "Exporting…" : "Transactions (CSV)"}
          </button>
          <button
            type="button"
            onClick={() => void handleExportJson()}
            disabled={exportingJson}
            className="btn-ghost inline-flex items-center gap-2 px-4 py-2.5 text-sm disabled:opacity-50"
          >
            <Download size={15} className={exportingJson ? "animate-pulse" : ""} />
            {exportingJson ? "Exporting…" : "Full export (JSON)"}
          </button>
        </div>
        <Link href="/privacy" className="link-accent mt-4 inline-block text-sm">
          Read our privacy policy →
        </Link>
        <div className="mt-6 border-t border-[var(--border)] pt-4">
          <button
            type="button"
            onClick={() => void handleDeleteAccount()}
            disabled={deleting || !profile}
            className="inline-flex items-center gap-2 rounded-xl border border-rose-500/30 px-4 py-2.5 text-sm text-rose-400 transition-colors hover:bg-rose-500/10 disabled:opacity-40"
          >
            <AlertTriangle size={15} />
            {deleting ? "Deleting…" : "Delete my account"}
          </button>
        </div>
      </section>
    </div>
  );
}

function PrefRow({
  label,
  desc,
  checked,
  onChange,
}: {
  label: string;
  desc: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <p className="text-sm font-medium text-[var(--foreground)]">{label}</p>
        <p className="mt-0.5 text-xs text-[var(--muted)]">{desc}</p>
      </div>
      <ToggleSwitch checked={checked} onChange={onChange} label={label} />
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
