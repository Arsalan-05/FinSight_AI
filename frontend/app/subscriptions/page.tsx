"use client";

import { MessageSquare, Receipt } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { useAuthReady } from "@/hooks/useAuthReady";
import { api } from "@/lib/api";
import type { SubscriptionItem } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function SubscriptionsPage() {
  const authReady = useAuthReady();
  const [items, setItems] = useState<SubscriptionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authReady) return;
    api
      .getSubscriptions()
      .then((res) => {
        setItems(res.items);
        setTotal(res.summary.estimated_monthly_total);
      })
      .catch(() => {
        setItems([]);
        setTotal(0);
      })
      .finally(() => setLoading(false));
  }, [authReady]);

  return (
    <div className="page-container max-w-3xl gap-6">
      <PageHeader
        eyebrow="Recurring"
        title="Subscriptions"
        subtitle="Recurring charges detected from your transaction history."
      />

      <div className="panel rounded-2xl p-6">
        <p className="text-[10px] font-medium uppercase tracking-wider text-[var(--muted)]">
          Estimated monthly total
        </p>
        <p className="mt-1 text-3xl font-semibold tabular-nums text-[var(--foreground)]">
          {loading ? "—" : formatCurrency(total)}
        </p>
        <p className="mt-1 text-sm text-[var(--muted)]">
          {items.length} recurring merchant{items.length !== 1 ? "s" : ""} detected
        </p>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 shimmer rounded-2xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="panel flex flex-col items-center gap-3 rounded-2xl py-14 text-center">
          <Receipt size={28} className="text-[var(--muted)]" />
          <p className="text-sm text-[var(--muted)]">
            No recurring charges detected yet. Import more transactions to find subscriptions.
          </p>
          <Link href="/transactions" className="btn-primary rounded-xl px-4 py-2 text-xs">
            Upload transactions
          </Link>
        </div>
      ) : (
        <ul className="panel flex flex-col divide-y divide-[var(--border)] rounded-2xl overflow-hidden">
          {items.map((item) => (
            <li
              key={item.merchant}
              className="flex flex-col gap-2 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[var(--foreground)]">
                  {item.merchant}
                </p>
                <p className="mt-0.5 text-xs text-[var(--muted)]">
                  {item.category} · {item.occurrences} charges · last {formatDate(item.last_date)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <div className="text-right">
                  <p className="text-sm font-semibold tabular-nums text-[var(--foreground)]">
                    ~{formatCurrency(item.estimated_monthly)}/mo
                  </p>
                  <p className="text-xs text-[var(--muted)]">avg {formatCurrency(item.amount)}</p>
                </div>
                <Link
                  href="/chat"
                  className="btn-ghost inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs"
                >
                  <MessageSquare size={12} />
                  Ask
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
