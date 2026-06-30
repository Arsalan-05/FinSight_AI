import { LogoMark } from "./LogoMark";

export { LogoMark };

export function LogoWordmark({
  subtitle = "Personal Finance",
  compact = false,
}: {
  subtitle?: string;
  compact?: boolean;
}) {
  return (
    <div className="min-w-0">
      <p
        className={[
          "truncate font-semibold tracking-tight text-gradient",
          compact ? "text-sm" : "text-base",
        ].join(" ")}
      >
        FinSight
      </p>
      {!compact && subtitle && (
        <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-[var(--muted)]">
          {subtitle}
        </p>
      )}
    </div>
  );
}

export function Logo({
  size = 40,
  subtitle,
  compact = false,
}: {
  size?: number;
  subtitle?: string;
  compact?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="flex shrink-0 items-center justify-center overflow-hidden rounded-xl shadow-lg shadow-teal-900/20"
        style={{ width: size, height: size }}
      >
        <LogoMark size={size} />
      </div>
      <LogoWordmark subtitle={subtitle} compact={compact} />
    </div>
  );
}
