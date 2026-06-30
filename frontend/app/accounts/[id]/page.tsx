"use client";

import {
  ArrowDownLeft,
  ArrowLeft,
  ArrowUpRight,
  CreditCard,
  MessageSquare,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { AccountTypeIcon } from "@/components/AccountTypeIcon";
import { KpiCard } from "@/components/ui/KpiCard";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import { chatUrl } from "@/lib/chat-url";
import type { Account, Transaction } from "@/lib/types";
import { getCategoryColor } from "@/lib/types";
import { formatCurrency, formatDate, formatDateShort, getDateRange } from "@/lib/utils";

const INSTITUTION_LABELS: Record<string, string> = {
  RBC: "Royal Bank of Canada",
  TD: "TD Canada Trust",
  BMO: "BMO",
  CIBC: "CIBC",
  Scotiabank: "Scotiabank",
};

export default function AccountDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const authReady = useAuthReady();
  const [account, setAccount] = useState<Account | null>(null);
  const [txs, setTxs] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authReady || !id) return;
    let active = true;
    const range = getDateRange(1);
    Promise.all([
      api.getAccount(id),
      api.getTransactions({ account_id: id, date_from: range.from, date_to: range.to, limit: 500 }),
    ])
      .then(([acc, list]) => {
        if (!active) return;
        setAccount(acc);
        setTxs(list.items);
        setError(null);
      })
      .catch((e) => {
        if (!active) return;
        setError(e instanceof Error ? e.message : "Account not found");
        setAccount(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [authReady, id]);

  const spend = txs.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
  const income = txs.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const netFlow = income - spend;

  const catMap: Record<string, number> = {};
  for (const tx of txs) {
    if (tx.amount < 0) catMap[tx.category] = (catMap[tx.category] ?? 0) + Math.abs(tx.amount);
  }
  const topCategories = Object.entries(catMap).sort(([, a], [, b]) => b - a).slice(0, 5);

  if (loading) {
    return (
      <div className="page-container">
        <div className="h-8 w-48 shimmer rounded-lg" />
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-28 shimmer rounded-2xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !account) {
    return (
      <div className="page-container">
        <Link href="/accounts" className="link-accent inline-flex items-center gap-1 text-sm">
          <ArrowLeft size={14} />
          Back to accounts
        </Link>
        <div className="panel mt-6 rounded-2xl p-8 text-center">
          <p className="text-sm text-[var(--muted)]">{error ?? "Account not found"}</p>
        </div>
      </div>
    );
  }

  const institution = INSTITUTION_LABELS[account.institution] ?? account.institution;

  return (
    <div className="page-container gap-6">
      <Link href="/accounts" className="link-accent inline-flex items-center gap-1 text-sm">
        <ArrowLeft size={14} />
        All accounts
      </Link>

      <PageHeader
        eyebrow={institution}
        title={account.name}
        subtitle={`${account.account_type.charAt(0).toUpperCase()}${account.account_type.slice(1)} · Added ${formatDate(account.created_at.slice(0, 10))}`}
        actions={
          <Link
            href={chatUrl(
              `Analyze spending and trends for my ${account.name} account (${institution}).`,
            )}
            className="btn-primary inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-medium"
          >
            <MessageSquare size={14} />
            Ask about this account
          </Link>
        }
      />

      <div className="panel flex items-center gap-4 rounded-2xl p-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--accent-soft)]">
          <AccountTypeIcon type={account.account_type} size={26} className="text-[var(--accent)]" />
        </div>
        <div>
          <p className="text-lg font-semibold text-[var(--foreground)]">{account.name}</p>
          <p className="text-sm text-[var(--muted)]">{institution}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard icon={<ArrowDownLeft size={15} />} label="30-day spend" value={formatCurrency(spend)} sub="Debits" accent="rose" />
        <KpiCard icon={<ArrowUpRight size={15} />} label="30-day income" value={formatCurrency(income)} sub="Credits" accent="emerald" />
        <KpiCard
          icon={<Wallet size={15} />}
          label="Net flow"
          value={formatCurrency(Math.abs(netFlow))}
          sub={netFlow >= 0 ? "Inflow" : "Outflow"}
          accent={netFlow >= 0 ? "emerald" : "rose"}
          neg={netFlow < 0}
        />
        <KpiCard icon={<CreditCard size={15} />} label="Transactions" value={String(txs.length)} sub="Last 30 days" accent="teal" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel rounded-2xl p-6">
          <h2 className="section-title mb-4">Spending by category</h2>
          {topCategories.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">No spending in the last 30 days.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {topCategories.map(([cat, total]) => (
                <li key={cat} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full" style={{ background: getCategoryColor(cat) }} />
                    {cat}
                  </span>
                  <span className="tabular-nums text-[var(--muted)]">{formatCurrency(total)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel rounded-2xl p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="section-title">Recent activity</h2>
            <Link href={`/transactions?account=${id}`} className="link-accent text-xs">
              View all →
            </Link>
          </div>
          {txs.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">No transactions yet for this account.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-[var(--border)]">
              {txs.slice(0, 12).map((tx) => (
                <li key={tx.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-[var(--foreground)]">{tx.description}</p>
                    <p className="text-xs text-[var(--muted)]">
                      {tx.category} · {formatDateShort(tx.transaction_date)}
                    </p>
                  </div>
                  <span
                    className={[
                      "shrink-0 text-sm font-medium tabular-nums",
                      tx.amount < 0 ? "text-red-400" : "text-emerald-400",
                    ].join(" ")}
                  >
                    {tx.amount < 0 ? "-" : "+"}
                    {formatCurrency(tx.amount)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
