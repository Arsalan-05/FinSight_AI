"use client";

import { FlaskConical, X } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";
import { useSearchParams } from "next/navigation";

export const DEMO_STORAGE_KEY = "finsight-demo-mode";

function readDemoFlag(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(DEMO_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

const noopSubscribe = () => () => {};

export function DemoBanner() {
  const searchParams = useSearchParams();
  const demoParam = searchParams.get("demo");
  const storedFlag = useSyncExternalStore(noopSubscribe, readDemoFlag, () => false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    try {
      if (demoParam === "1") localStorage.setItem(DEMO_STORAGE_KEY, "1");
      else if (demoParam === "0") localStorage.removeItem(DEMO_STORAGE_KEY);
    } catch {
      /* private mode — banner still follows the query param */
    }
  }, [demoParam]);

  const visible = demoParam === "1" || (demoParam !== "0" && storedFlag);
  if (!visible || dismissed) return null;

  return (
    <div
      role="status"
      className="mb-4 flex items-center gap-3 rounded-xl border border-[var(--border-glow)] bg-[var(--accent-soft)] px-4 py-2.5 text-sm text-[var(--foreground)]"
    >
      <FlaskConical size={16} className="shrink-0 text-[var(--accent)]" />
      <p className="min-w-0 flex-1 text-xs sm:text-sm">
        Demo mode — read-only seeded persona
      </p>
      <button
        type="button"
        className="icon-btn h-8 w-8"
        aria-label="Dismiss demo banner"
        onClick={() => setDismissed(true)}
      >
        <X size={14} />
      </button>
    </div>
  );
}
