"use client";

import { ArrowRight, Building2, Upload } from "lucide-react";
import Link from "next/link";

export function OnboardingBanner() {
  return (
    <div className="panel rounded-2xl border-indigo-500/30 bg-indigo-500/5 p-6">
      <h2 className="text-lg font-semibold text-zinc-100">Welcome to FinSight AI</h2>
      <p className="mt-2 max-w-2xl text-sm text-zinc-400">
        Get started in three steps: create a Canadian bank account, upload a CSV export
        (RBC, TD, Scotiabank, BMO, CIBC, Simplii, Tangerine, EQ Bank), then ask the agent
        anything about your spending.
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <Link
          href="/accounts"
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
        >
          <Building2 size={16} />
          Add account
        </Link>
        <Link
          href="/transactions"
          className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 px-4 py-2.5 text-sm text-zinc-300 transition-colors hover:border-zinc-600 hover:text-zinc-100"
        >
          <Upload size={16} />
          Upload bank CSV
        </Link>
        <a
          href="/samples/rbc_sample.csv"
          download
          className="inline-flex items-center gap-2 rounded-xl border border-zinc-800 px-4 py-2.5 text-sm text-zinc-500 transition-colors hover:text-zinc-300"
        >
          Download sample RBC CSV
          <ArrowRight size={14} />
        </a>
      </div>
    </div>
  );
}
