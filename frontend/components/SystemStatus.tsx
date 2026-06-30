"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

type Status = "checking" | "online" | "degraded" | "offline";

export default function SystemStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const [health, ready] = await Promise.all([
          api.health(),
          fetch(
            `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health/ready`,
          ).then((r) => r.json() as Promise<{ status?: string; database?: boolean }>),
        ]);
        if (cancelled) return;
        const dbOk = ready.database === true;
        setStatus(dbOk ? "online" : "degraded");
        setDetail(
          dbOk
            ? `API ${health.version ?? ""} · ${health.llm_provider ?? "llm"}`
            : "API up · database unreachable",
        );
      } catch {
        if (!cancelled) {
          setStatus("offline");
          setDetail("Backend offline");
        }
      }
    };
    void check();
    const id = setInterval(() => void check(), 60_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const color =
    status === "online"
      ? "bg-emerald-500"
      : status === "degraded"
        ? "bg-amber-500"
        : status === "offline"
          ? "bg-rose-500"
          : "bg-zinc-500";

  return (
    <div
      className="hidden items-center gap-2 text-[10px] text-zinc-500 md:flex"
      title={detail || "System status"}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${color} ${status === "checking" ? "animate-pulse" : ""}`} />
      <span className="max-w-[140px] truncate">{detail || "Checking…"}</span>
    </div>
  );
}
