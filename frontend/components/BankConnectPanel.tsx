"use client";

import {
  Building2,
  FileSpreadsheet,
  Landmark,
  RefreshCw,
  ShieldCheck,
  Unlink,
} from "lucide-react";
import Script from "next/script";
import { useCallback, useEffect, useState } from "react";

import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import type { BankConnection, PlaidStatus } from "@/lib/types";

type PlaidHandler = { open: () => void; destroy: () => void };

declare global {
  interface Window {
    Plaid?: {
      create: (config: {
        token: string;
        onSuccess: (public_token: string, metadata: { institution?: { name?: string } }) => void;
        onExit: (err: { display_message?: string } | null) => void;
      }) => PlaidHandler;
    };
  }
}

export default function BankConnectPanel() {
  const { toast } = useToast();
  const [status, setStatus] = useState<PlaidStatus | null>(null);
  const [connections, setConnections] = useState<BankConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [scriptReady, setScriptReady] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    Promise.all([api.getPlaidStatus(), api.listBankConnections().catch(() => [])])
      .then(([s, c]) => {
        setStatus(s);
        setConnections(c);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const openPlaidLink = async () => {
    if (!window.Plaid) {
      toast("Plaid is still loading — try again in a moment", "error");
      return;
    }
    setLinking(true);
    try {
      const { link_token } = await api.createPlaidLinkToken();
      const handler = window.Plaid.create({
        token: link_token,
        onSuccess: (public_token, metadata) => {
          void api
            .exchangePlaidToken(public_token, metadata.institution?.name)
            .then(() => {
              toast("Bank connected — transactions syncing");
              refresh();
            })
            .catch((e: Error) => toast(e.message, "error"))
            .finally(() => setLinking(false));
        },
        onExit: (err) => {
          setLinking(false);
          if (err?.display_message) toast(err.display_message, "error");
        },
      });
      handler.open();
    } catch (e) {
      setLinking(false);
      toast(e instanceof Error ? e.message : "Could not start bank link", "error");
    }
  };

  const handleSync = () => {
    setSyncing(true);
    void api
      .syncBankConnections()
      .then((results) => {
        const added = results.reduce((n, r) => n + (r.added ?? 0), 0);
        toast(added > 0 ? `Synced ${added} new transactions` : "Already up to date");
        refresh();
      })
      .catch((e: Error) => toast(e.message, "error"))
      .finally(() => setSyncing(false));
  };

  const handleDisconnect = (id: string) => {
    void api
      .disconnectBank(id)
      .then(() => {
        toast("Bank disconnected");
        setConnections((prev) => prev.filter((c) => c.id !== id));
      })
      .catch((e: Error) => toast(e.message, "error"));
  };

  return (
    <>
      <Script
        src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"
        strategy="lazyOnload"
        onReady={() => setScriptReady(true)}
      />
      <section className="panel panel-glow overflow-hidden rounded-2xl p-0">
        <div className="border-b border-[var(--border)] bg-gradient-to-r from-teal-500/10 via-blue-600/5 to-transparent px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-500/15 text-teal-400">
              <Landmark size={20} />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="section-title">Connected banks</h2>
              <p className="mt-1 text-xs leading-relaxed text-[var(--muted)]">
                Secure read-only sync via Plaid. Your credentials stay with your bank —
                FinSight only receives transaction data you authorize.
              </p>
            </div>
            <ShieldCheck size={18} className="shrink-0 text-emerald-500/80" aria-hidden />
          </div>
        </div>

        <div className="flex flex-col gap-4 p-5">
          {loading ? (
            <div className="h-20 shimmer rounded-xl" />
          ) : !status?.enabled ? (
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
              <p className="text-sm font-medium text-[var(--foreground)]">Bank linking unavailable</p>
              <p className="mt-1 text-xs text-[var(--muted)]">
                Connect a bank account once linking is enabled for your workspace, or import
                transactions via CSV from Accounts.
              </p>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void openPlaidLink()}
                disabled={linking || !scriptReady}
                className="btn-primary inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium disabled:opacity-50"
              >
                <Building2 size={15} />
                {linking ? "Connecting…" : "Link bank account"}
              </button>
              {connections.length > 0 && (
                <button
                  type="button"
                  onClick={handleSync}
                  disabled={syncing}
                  className="btn-ghost inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm"
                >
                  <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
                  Sync now
                </button>
              )}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
              <FileSpreadsheet size={16} className="mt-0.5 shrink-0 text-[var(--accent)]" />
              <div>
                <p className="text-xs font-medium text-[var(--foreground)]">Import statements</p>
                <p className="mt-0.5 text-[11px] text-[var(--muted)]">
                  Upload CSV exports from RBC, TD, CIBC, BMO, and more
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
              <ShieldCheck size={16} className="mt-0.5 shrink-0 text-emerald-400" />
              <div>
                <p className="text-xs font-medium text-[var(--foreground)]">Bank-level security</p>
                <p className="mt-0.5 text-[11px] text-[var(--muted)]">
                  Read-only access — you approve every connection
                </p>
              </div>
            </div>
          </div>

          {connections.length > 0 && (
            <ul className="flex flex-col gap-2">
              {connections.map((c) => (
                <li
                  key={c.id}
                  className="flex items-center justify-between rounded-xl border border-emerald-500/15 bg-emerald-500/5 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-[var(--foreground)]">{c.institution_name}</p>
                    <p className="text-[11px] text-[var(--muted)]">
                      {c.last_synced_at
                        ? `Last sync ${new Date(c.last_synced_at).toLocaleString()}`
                        : "Connected"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDisconnect(c.id)}
                    className="btn-ghost flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-zinc-500 hover:text-rose-400"
                    aria-label="Disconnect bank"
                  >
                    <Unlink size={13} />
                    Disconnect
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </>
  );
}
