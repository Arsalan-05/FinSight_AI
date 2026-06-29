"use client";

import {
  Activity,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  Database,
  Download,
  RefreshCw,
  Server,
  Sparkles,
  Target,
  Trash2,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuthReady } from "@/hooks/useAuthReady";
import type { FinancialGoal } from "@/lib/types";
import { getApiKey, setApiKey } from "@/lib/auth";
import { isSupabaseConfigured } from "@/lib/supabase/client";
import { exportToCsv } from "@/lib/utils";
import { useToast } from "@/contexts/ToastContext";

interface Stats {
  users: number;
  accounts: number;
  transactions: number;
  embeddingEnabled: boolean;
  apiHealthy: boolean;
  environment: string;
  supabaseConfigured: boolean;
  profileEmail: string | null;
  profileSynced: boolean;
  dbHost: string | null;
  usingSupabaseDb: boolean;
  dbConfigured: boolean;
}

export default function SettingsPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [apiKey, setApiKeyState] = useState(() =>
    typeof window === "undefined" ? "" : getApiKey(),
  );
  const [goals, setGoals] = useState<FinancialGoal[]>([]);
  const [goalTitle, setGoalTitle] = useState("");
  const [goalAmount, setGoalAmount] = useState("");

  const fetchStats = useCallback(() => {
    const supabaseConfigured = isSupabaseConfigured();
    const base = Promise.all([
      api.health(),
      api.healthDb(),
      api.getAccounts(),
      api.getTransactions({ limit: 1 }),
      api.search("test", 1),
    ]);
    const profile = supabaseConfigured
      ? api.getMe()
          .then((u) => ({ email: u.email, synced: true, userCount: 1 }))
          .catch(() => ({ email: null as string | null, synced: false, userCount: 0 }))
      : Promise.resolve({ email: null as string | null, synced: false, userCount: 0 });

    return Promise.all([base, profile, supabaseConfigured ? Promise.resolve(null) : api.getUsers()])
      .then(([[health, dbHealth, accounts, txList, searchRes], prof, users]) => ({
        users: supabaseConfigured ? prof.userCount : (users?.length ?? 0),
        accounts: accounts.length,
        transactions: txList.total,
        embeddingEnabled: searchRes.embedding_enabled,
        apiHealthy: health.status === "ok",
        environment: health.environment,
        supabaseConfigured,
        profileEmail: prof.email,
        profileSynced: prof.synced,
        dbHost: dbHealth.host,
        usingSupabaseDb: dbHealth.using_supabase_postgres,
        dbConfigured: dbHealth.configured,
      }));
  }, []);

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    fetchStats().then((s) => {
      if (active) { setStats(s); setLoading(false); }
    }).catch(() => {
      if (active) setLoading(false);
    });
    if (isSupabaseConfigured()) {
      api.getGoals().then((g) => { if (active) setGoals(g); }).catch(() => {});
    }
    return () => { active = false; };
  }, [authReady, fetchStats]);

  const handleRefresh = () => {
    setLoading(true);
    fetchStats().then((s) => { setStats(s); setLoading(false); });
  };

  const handleExportAll = async () => {
    setExporting(true);
    try {
      const txs = await api.getAllTransactions("2000-01-01", new Date().toISOString().slice(0, 10));
      exportToCsv("finsight-all-transactions.csv", [
        ["ID", "Account ID", "Date", "Description", "Amount", "Category", "Merchant", "Notes"],
        ...txs.map((t) => [
          t.id, t.account_id, t.transaction_date, t.description,
          String(t.amount), t.category, t.merchant ?? "", t.notes ?? "",
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-zinc-50">Settings</h1>
          <p className="mt-0.5 text-sm text-zinc-500">System status and data management</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="flex h-8 w-8 items-center justify-center panel rounded-xl text-zinc-400 hover:text-zinc-100 disabled:opacity-40"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* System Health */}
      <section className="panel rounded-2xl p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Activity size={15} className="text-zinc-500" /> System Status
        </h2>
        <div className="flex flex-col gap-3">
          <StatusRow
            icon={<Server size={14} />}
            label="FastAPI Backend"
            description="http://localhost:8000"
            ok={stats?.apiHealthy ?? null}
            loading={loading}
            detail={stats?.environment}
          />
          <StatusRow
            icon={<Sparkles size={14} />}
            label="Supabase Auth"
            description={
              stats?.supabaseConfigured
                ? "Google OAuth + JWT → backend user sync"
                : "Set NEXT_PUBLIC_SUPABASE_* in frontend/.env.local"
            }
            ok={stats?.supabaseConfigured ? (stats.profileSynced ? true : null) : null}
            loading={loading}
            detail={stats?.profileEmail ?? undefined}
          />
          <StatusRow
            icon={<Database size={14} />}
            label="PostgreSQL + pgvector"
            description={
              stats?.usingSupabaseDb
                ? `Supabase hosted — ${stats.dbHost ?? "connected"}`
                : !stats?.dbConfigured && stats?.supabaseConfigured
                  ? "Set DATABASE_URL in .env — see DOCUMENTATION.md §14"
                  : "Local Docker — data not in Supabase cloud"
            }
            ok={
              stats?.usingSupabaseDb
                ? true
                : stats?.dbConfigured === false
                  ? false
                  : stats?.apiHealthy ?? null
            }
            loading={loading}
          />
          <StatusRow
            icon={<Sparkles size={14} />}
            label="Voyage AI Embeddings"
            description={stats?.embeddingEnabled ? "voyage-3 (1024-dim) — ready" : "Set VOYAGE_API_KEY to enable semantic search"}
            ok={stats?.embeddingEnabled ?? null}
            loading={loading}
          />
          <StatusRow
            icon={<BrainCircuit size={14} />}
            label="LangGraph Agent"
            description="Ollama llama3.2 + ReAct tools — POST /chat SSE"
            ok={stats?.apiHealthy ?? null}
            loading={loading}
          />
        </div>
      </section>

      {/* API Key */}
      <section className="panel rounded-2xl p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Server size={15} className="text-zinc-500" /> API Access
        </h2>
        <p className="mb-3 text-xs text-zinc-600">
          Optional. Set <code className="text-zinc-400">FINSIGHT_API_KEY</code> on the backend to
          require an <code className="text-zinc-400">X-API-Key</code> header on all routes except
          /health.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKeyState(e.target.value)}
            placeholder="API key (stored in browser localStorage)"
            className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-indigo-500/50 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => {
              setApiKey(apiKey);
              toast(apiKey.trim() ? "API key saved" : "API key cleared");
            }}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Save key
          </button>
        </div>
      </section>

      {/* Financial Goals */}
      {stats?.supabaseConfigured && (
        <section className="panel rounded-2xl p-5">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-200">
            <Target size={15} className="text-zinc-500" /> Financial Goals
          </h2>
          <p className="mb-4 text-xs text-zinc-500">
            Goals persist across chat sessions — the agent remembers what you are saving for.
          </p>
          <div className="mb-4 flex flex-col gap-2 sm:flex-row">
            <input
              value={goalTitle}
              onChange={(e) => setGoalTitle(e.target.value)}
              placeholder="e.g. Fall 2026 rent buffer"
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200"
            />
            <input
              value={goalAmount}
              onChange={(e) => setGoalAmount(e.target.value)}
              placeholder="Target $"
              type="number"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 sm:w-28"
            />
            <button
              type="button"
              onClick={() => {
                if (!goalTitle.trim()) return;
                void api
                  .createGoal({
                    title: goalTitle.trim(),
                    target_amount: goalAmount ? parseFloat(goalAmount) : undefined,
                  })
                  .then((g) => {
                    setGoals((prev) => [...prev, g]);
                    setGoalTitle("");
                    setGoalAmount("");
                    toast("Goal saved");
                  })
                  .catch(() => toast("Sign in to save goals", "error"));
              }}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-500"
            >
              Add goal
            </button>
          </div>
          <ul className="flex flex-col gap-2">
            {goals.map((g) => (
              <li key={g.id} className="flex items-center justify-between rounded-lg bg-zinc-950 px-3 py-2">
                <div>
                  <p className="text-sm text-zinc-300">{g.title}</p>
                  {g.target_amount != null && (
                    <p className="text-xs text-zinc-600">Target ${g.target_amount.toLocaleString()}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => void api.deleteGoal(g.id).then(() => {
                    setGoals((prev) => prev.filter((x) => x.id !== g.id));
                  })}
                  className="text-zinc-600 hover:text-rose-400"
                  aria-label="Delete goal"
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
            {goals.length === 0 && (
              <p className="text-xs text-zinc-600">No goals yet — add one above.</p>
            )}
          </ul>
        </section>
      )}

      {/* Data Statistics */}
      <section className="panel rounded-2xl p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Database size={15} className="text-zinc-500" /> Data
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <DataStat label="Users" value={stats?.users ?? null} loading={loading} />
          <DataStat label="Accounts" value={stats?.accounts ?? null} loading={loading} />
          <DataStat label="Transactions" value={stats?.transactions ?? null} loading={loading} />
        </div>
      </section>

      {/* Actions */}
      <section className="panel rounded-2xl p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Download size={15} className="text-zinc-500" /> Data Management
        </h2>
        <div className="flex flex-col gap-2">
          <ActionRow
            icon={<Download size={14} />}
            label="Export All Transactions"
            description="Download every transaction as a CSV file"
            onClick={() => void handleExportAll()}
            loading={exporting}
          />
          <ActionRow
            icon={<RefreshCw size={14} />}
            label="API Documentation"
            description="Open Swagger UI for the FastAPI backend"
            onClick={() => window.open("http://localhost:8000/docs", "_blank")}
          />
        </div>
      </section>

      {/* Environment info */}
      <section className="panel rounded-2xl p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Server size={15} className="text-zinc-500" /> Environment
        </h2>
        <div className="flex flex-col gap-2 font-mono text-xs text-zinc-500">
          {[
            ["NEXT_PUBLIC_API_URL", process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"],
            ["NODE_ENV", process.env.NODE_ENV ?? "development"],
            ["Backend env", stats?.environment ?? "…"],
          ].map(([k, v]) => (
            <div key={k} className="flex gap-4">
              <span className="w-44 shrink-0 text-zinc-600">{k}</span>
              <span className="text-zinc-400">{v}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Roadmap */}
      <section className="panel rounded-2xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-zinc-200">Build Progress</h2>
        <div className="flex flex-col gap-2">
          {[
            { week: "Week 1", title: "Scaffolding & Docker", done: true },
            { week: "Week 2", title: "Data Layer (CRUD, CSV, Migrations)", done: true },
            { week: "Week 3", title: "RAG Pipeline (Voyage AI + pgvector)", done: true },
            { week: "Week 4", title: "LangGraph Agent Core", done: true },
            { week: "Week 5", title: "FastAPI /chat SSE Endpoint + MCP", done: true },
            { week: "Week 6", title: "Streaming Chat UI", done: true },
            { week: "Week 7", title: "Supabase Auth + Premium UI + CI", done: true },
            { week: "Week 8", title: "Testing, Polish, HNSW Index", done: true },
            { week: "Complete", title: "Canadian banks, insights, citations, goals", done: true },
          ].map(({ week, title, done }) => (
            <div key={week} className="flex items-center gap-3 rounded-lg px-3 py-2.5">
              {done ? (
                <CheckCircle2 size={15} className="text-emerald-500" />
              ) : (
                <div className="h-3.5 w-3.5 rounded-full border border-zinc-700" />
              )}
              <span className="w-16 shrink-0 text-xs text-zinc-600">{week}</span>
              <span className={["text-sm", done ? "text-zinc-300" : "text-zinc-600"].join(" ")}>
                {title}
              </span>
              {done && (
                <span className="ml-auto rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-400">
                  Done
                </span>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusRow({
  icon, label, description, ok, loading, detail, badge,
}: {
  icon: React.ReactNode; label: string; description: string;
  ok: boolean | null; loading: boolean; detail?: string; badge?: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-zinc-800/50 bg-zinc-800/30 px-4 py-3">
      <span className="mt-0.5 text-zinc-500">{icon}</span>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-zinc-300">{label}</p>
          {badge && (
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-500">{badge}</span>
          )}
          {detail && <span className="text-xs text-zinc-600">{detail}</span>}
        </div>
        <p className="mt-0.5 text-xs text-zinc-600">{description}</p>
      </div>
      <div className="mt-0.5">
        {loading ? (
          <div className="h-4 w-16 shimmer rounded" />
        ) : ok === null ? (
          <span className="flex items-center gap-1 text-xs text-zinc-600">
            <div className="h-1.5 w-1.5 rounded-full bg-zinc-700" /> Pending
          </span>
        ) : ok ? (
          <span className="flex items-center gap-1 text-xs text-emerald-400">
            <CheckCircle2 size={13} /> OK
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-red-400">
            <XCircle size={13} /> Error
          </span>
        )}
      </div>
    </div>
  );
}

function DataStat({ label, value, loading }: { label: string; value: number | null; loading: boolean }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-zinc-800/50 bg-zinc-800/30 p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      {loading ? (
        <div className="h-7 w-12 shimmer rounded" />
      ) : (
        <p className="text-2xl font-semibold text-zinc-100">{value?.toLocaleString() ?? "—"}</p>
      )}
    </div>
  );
}

function ActionRow({ icon, label, description, onClick, loading }: {
  icon: React.ReactNode; label: string; description: string; onClick: () => void; loading?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="flex w-full items-center gap-3 rounded-lg border border-zinc-800/50 bg-zinc-800/30 px-4 py-3 text-left transition-colors hover:border-zinc-700 hover:bg-zinc-800 disabled:opacity-40"
    >
      <span className="text-zinc-400">{icon}</span>
      <div className="flex-1">
        <p className="text-sm font-medium text-zinc-300">{label}</p>
        <p className="mt-0.5 text-xs text-zinc-600">{description}</p>
      </div>
      {loading ? (
        <RefreshCw size={14} className="animate-spin text-zinc-500" />
      ) : (
        <ChevronRight size={14} className="text-zinc-700" />
      )}
    </button>
  );
}
