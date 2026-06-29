import type { CSSProperties, ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  titleAccent,
  subtitle,
  actions,
  large,
}: {
  eyebrow?: string;
  title: string;
  titleAccent?: string;
  subtitle?: string;
  actions?: ReactNode;
  large?: boolean;
}) {
  return (
    <header className="page-header stagger-item" style={{ "--stagger": 0 } as CSSProperties}>
      <div className="min-w-0 flex-1">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className={large ? "hero-title mt-1" : "page-title mt-1"}>
          {title}
          {titleAccent && <span className="text-gradient"> {titleAccent}</span>}
        </h1>
        {subtitle && <p className="page-subtitle mt-1.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
