import type { CSSProperties } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";

const ACCENT: Record<string, string> = {
  indigo: "kpi-accent-indigo",
  sky: "kpi-accent-sky",
  rose: "kpi-accent-rose",
  emerald: "kpi-accent-emerald",
};

export function KpiCard({
  icon,
  label,
  value,
  sub,
  accent,
  trend,
  neg,
  loading,
  stagger = 0,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  accent: "indigo" | "sky" | "rose" | "emerald";
  trend?: number | null;
  neg?: boolean;
  loading?: boolean;
  stagger?: number;
}) {
  return (
    <div
      className={`kpi-card panel-interactive stagger-item ${ACCENT[accent]}`}
      style={{ "--stagger": stagger } as CSSProperties}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted)]">
          {label}
        </span>
        <span className="kpi-icon">{icon}</span>
      </div>
      {loading ? (
        <div className="shimmer h-9 rounded-lg" />
      ) : (
        <p className={["text-2xl font-semibold tabular-nums tracking-tight", neg ? "text-rose-400" : ""].join(" ")}>
          {neg ? "−" : ""}{value}
        </p>
      )}
      <p className="flex items-center gap-1 truncate text-xs text-[var(--muted)]">
        {trend !== null && trend !== undefined && (
          trend < 0
            ? <ArrowDownRight size={11} className="text-emerald-400" />
            : <ArrowUpRight size={11} className="text-rose-400" />
        )}
        {sub}
      </p>
    </div>
  );
}
