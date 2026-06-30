"use client";

import { ArrowRight, Building2, Upload } from "lucide-react";
import Link from "next/link";

export function OnboardingBanner() {
  return (
    <div className="panel rounded-2xl border-[var(--border-glow)] bg-[var(--accent-soft)] p-6">
      <h2 className="text-lg font-semibold text-[var(--foreground)]">Welcome to FinSight</h2>
      <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
        Get started in three steps: add a Canadian bank account, upload a CSV export
        (RBC, TD, Scotiabank, BMO, CIBC, Simplii, Tangerine, EQ Bank), then ask the agent
        anything about your spending.
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <Link
          href="/accounts"
          className="btn-primary inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium"
        >
          <Building2 size={16} />
          Add account
        </Link>
        <Link
          href="/transactions"
          className="btn-ghost inline-flex items-center gap-2 px-4 py-2.5 text-sm"
        >
          <Upload size={16} />
          Upload bank CSV
        </Link>
        <a
          href="/samples/rbc_sample.csv"
          download
          className="btn-ghost inline-flex items-center gap-2 px-4 py-2.5 text-sm text-[var(--muted)]"
        >
          Download sample RBC CSV
          <ArrowRight size={14} />
        </a>
      </div>
    </div>
  );
}
