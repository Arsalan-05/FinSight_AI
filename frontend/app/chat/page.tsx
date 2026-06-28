"use client";

import {
  BrainCircuit,
  Code2,
  Database,
  MessageSquare,
  Search,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

const UPCOMING = [
  {
    icon: <BrainCircuit size={16} />,
    week: "Week 4",
    title: "LangGraph Agent Core",
    desc: "ReAct-style stateful agent with tool calling, memory across turns, and spending aggregator.",
    color: "text-indigo-400 bg-indigo-500/10",
  },
  {
    icon: <Code2 size={16} />,
    week: "Week 5",
    title: "FastAPI Chat Endpoint",
    desc: "POST /chat with server-sent events streaming, MCP tool servers, and session persistence.",
    color: "text-sky-400 bg-sky-500/10",
  },
  {
    icon: <MessageSquare size={16} />,
    week: "Week 6",
    title: "Chat UI",
    desc: "Full streaming chat interface wired to the real agent — this page.",
    color: "text-violet-400 bg-violet-500/10",
  },
];

export default function ChatPage() {
  return (
    <div className="flex flex-col gap-8 p-6 pt-16 md:pt-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold text-zinc-50">Chat Agent</h1>
        <p className="mt-0.5 text-sm text-zinc-500">Coming in Week 4 — LangGraph + Claude</p>
      </div>

      {/* Chat mockup */}
      <div className="flex flex-col gap-0 overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900">
        {/* Fake toolbar */}
        <div className="flex items-center gap-3 border-b border-zinc-800 px-4 py-3">
          <BrainCircuit size={16} className="text-indigo-400" />
          <span className="text-sm font-medium text-zinc-300">FinSight Agent</span>
          <span className="ml-auto rounded-full bg-zinc-800 px-2.5 py-0.5 text-xs text-zinc-500">
            claude-sonnet-4-6
          </span>
        </div>

        {/* Fake messages */}
        <div className="flex flex-col gap-4 p-5">
          <FakeUserMsg text="What did I spend on food last month?" />
          <FakeAgentMsg>
            <p className="text-sm text-zinc-300">
              Based on your transactions, here&apos;s your food spending for{" "}
              <span className="text-indigo-300">June 2026</span>:
            </p>
            <ul className="mt-2 flex flex-col gap-1 text-sm">
              <li className="flex justify-between">
                <span className="text-zinc-400">Dining out</span>
                <span className="font-medium text-zinc-200 tabular-nums">$284.50</span>
              </li>
              <li className="flex justify-between">
                <span className="text-zinc-400">Groceries</span>
                <span className="font-medium text-zinc-200 tabular-nums">$421.30</span>
              </li>
              <li className="mt-1 flex justify-between border-t border-zinc-800 pt-1">
                <span className="font-medium text-zinc-300">Total food</span>
                <span className="font-semibold text-red-400 tabular-nums">$705.80</span>
              </li>
            </ul>
            <p className="mt-2 text-xs text-zinc-500">
              Retrieved via semantic search · 14 transactions matched
            </p>
          </FakeAgentMsg>
          <FakeUserMsg text="Which grocery store do I use most?" />
          <FakeAgentMsg>
            <p className="text-sm text-zinc-400 italic">
              Agent is thinking…{" "}
              <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-indigo-500 align-middle" />
            </p>
          </FakeAgentMsg>
        </div>

        {/* Fake input */}
        <div className="border-t border-zinc-800 p-4">
          <div className="flex cursor-not-allowed items-center gap-3 rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-3 opacity-50">
            <span className="flex-1 text-sm text-zinc-600">Ask anything about your finances…</span>
            <Sparkles size={15} className="text-zinc-600" />
          </div>
        </div>
      </div>

      {/* Status card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h2 className="mb-4 text-sm font-semibold text-zinc-200">
          What&apos;s already built
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <BuiltCard icon={<Database size={14} />} label="Data Layer" status="done" href="/accounts">
            Users, accounts, transactions — full CRUD + CSV ingest
          </BuiltCard>
          <BuiltCard icon={<Search size={14} />} label="RAG Pipeline" status="done" href="/search">
            Voyage AI voyage-3 embeddings + pgvector cosine search
          </BuiltCard>
          <BuiltCard icon={<MessageSquare size={14} />} label="Chat Agent" status="pending" href="/chat">
            LangGraph ReAct graph with memory — building in Week 4
          </BuiltCard>
        </div>
      </div>

      {/* Upcoming roadmap */}
      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-zinc-400">Upcoming</h2>
        <div className="flex flex-col gap-3">
          {UPCOMING.map(({ icon, week, title, desc, color }) => (
            <div
              key={week}
              className="flex items-start gap-4 rounded-xl border border-zinc-800 bg-zinc-900 p-4"
            >
              <span className={`mt-0.5 rounded-lg p-2 ${color}`}>{icon}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-zinc-500">{week}</span>
                  <h3 className="text-sm font-medium text-zinc-200">{title}</h3>
                </div>
                <p className="mt-1 text-xs text-zinc-500">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function FakeUserMsg({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[70%] rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-sm text-white">
        {text}
      </div>
    </div>
  );
}

function FakeAgentMsg({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20">
        <BrainCircuit size={13} className="text-indigo-400" />
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-tl-sm border border-zinc-800 bg-zinc-950 px-4 py-3">
        {children}
      </div>
    </div>
  );
}

function BuiltCard({
  icon,
  label,
  status,
  href,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  status: "done" | "pending";
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="flex flex-col gap-2 rounded-lg border border-zinc-800 bg-zinc-950 p-4 transition-colors hover:border-zinc-700"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-zinc-400">{icon}<span className="text-xs font-medium">{label}</span></div>
        <span className={[
          "rounded-full px-2 py-0.5 text-[10px] font-medium",
          status === "done"
            ? "bg-emerald-500/10 text-emerald-400"
            : "bg-zinc-800 text-zinc-600",
        ].join(" ")}>
          {status === "done" ? "✓ Done" : "Pending"}
        </span>
      </div>
      <p className="text-xs text-zinc-600">{children}</p>
    </Link>
  );
}
