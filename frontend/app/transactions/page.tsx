"use client";

import {
  ArrowDownUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Download,
  Plus,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { useAuthReady } from "@/hooks/useAuthReady";
import type { Account, Transaction } from "@/lib/types";
import { getCategoryColor } from "@/lib/types";
import { exportToCsv, formatCurrency, formatDate } from "@/lib/utils";
import { useToast } from "@/contexts/ToastContext";

const PAGE_SIZE = 20;

const CATEGORIES = [
  "Dining", "Groceries", "Transport", "Housing", "Shopping",
  "Subscriptions", "Healthcare", "Income", "Entertainment", "Utilities",
  "Uncategorized",
];

type SortKey = "transaction_date" | "description" | "amount" | "category";
type SortDir = "asc" | "desc";

function sortTransactions(items: Transaction[], key: SortKey, dir: SortDir): Transaction[] {
  return [...items].sort((a, b) => {
    let cmp = 0;
    if (key === "amount") cmp = a.amount - b.amount;
    else if (key === "transaction_date") cmp = a.transaction_date.localeCompare(b.transaction_date);
    else cmp = String(a[key]).localeCompare(String(b[key]));
    return dir === "asc" ? cmp : -cmp;
  });
}

export default function TransactionsPage() {
  const { toast } = useToast();
  const authReady = useAuthReady();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>("transaction_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Filters
  const [filterAccount, setFilterAccount] = useState("");

  useEffect(() => {
    const acc = new URLSearchParams(window.location.search).get("account");
    if (acc) setFilterAccount(acc);
  }, []);
  const [filterCategory, setFilterCategory] = useState("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");

  // Modals
  const [showCreate, setShowCreate] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const fetchPage = useCallback(async () => {
    const [accs, txList] = await Promise.all([
      api.getAccounts(),
      api.getTransactions({
        account_id: filterAccount || undefined,
        category: filterCategory || undefined,
        date_from: filterFrom || undefined,
        date_to: filterTo || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    ]);
    return { accs, txList };
  }, [filterAccount, filterCategory, filterFrom, filterTo, page]);

  useEffect(() => {
    if (!authReady) return;
    let active = true;
    fetchPage().then(({ accs, txList }) => {
      if (!active) return;
      setAccounts(accs);
      setTransactions(txList.items);
      setTotal(txList.total);
      setSelected(new Set());
      setLoading(false);
    }).catch(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [authReady, fetchPage]);

  const loadData = useCallback(() => {
    setLoading(true);
    fetchPage().then(({ accs, txList }) => {
      setAccounts(accs);
      setTransactions(txList.items);
      setTotal(txList.total);
      setSelected(new Set());
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [fetchPage]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const sorted = sortTransactions(transactions, sortKey, sortDir);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected(selected.size === sorted.length ? new Set() : new Set(sorted.map((t) => t.id)));
  };

  const handleBulkDelete = async () => {
    if (!selected.size) return;
    setBulkDeleting(true);
    try {
      await Promise.all([...selected].map((id) => api.deleteTransaction(id)));
      toast(`Deleted ${selected.size} transaction${selected.size > 1 ? "s" : ""}`);
      loadData();
    } catch {
      toast("Some deletions failed", "error");
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteTransaction(id);
      toast("Transaction deleted");
      loadData();
    } catch {
      toast("Delete failed", "error");
    }
  };

  const handleCategoryChange = async (id: string, category: string) => {
    try {
      await api.updateTransaction(id, { category });
      setTransactions((prev) =>
        prev.map((t) => (t.id === id ? { ...t, category } : t)),
      );
      toast("Category updated");
    } catch {
      toast("Could not update category", "error");
    }
  };

  const handleExport = () => {
    exportToCsv(`transactions-${new Date().toISOString().slice(0, 10)}.csv`, [
      ["Date", "Description", "Amount", "Category", "Merchant", "Notes", "ID"],
      ...sorted.map((t) => [
        t.transaction_date, t.description, String(t.amount),
        t.category, t.merchant ?? "", t.notes ?? "", t.id,
      ]),
    ]);
    toast("Exported current view");
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const SortIcon = ({ col }: { col: SortKey }) =>
    sortKey === col
      ? sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />
      : <ArrowDownUp size={12} className="opacity-30" />;

  return (
    <div className="flex flex-col gap-5 p-6 pt-16 md:pt-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">Transactions</h1>
          <p className="mt-0.5 text-sm text-[var(--muted)]">{total.toLocaleString()} records</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleExport}
            className="btn-ghost flex items-center gap-1.5 px-3 py-2 text-xs font-medium">
            <Download size={13} /> Export
          </button>
          <button onClick={() => setShowUpload(true)}
            className="btn-ghost flex items-center gap-1.5 px-3 py-2 text-xs font-medium">
            <Upload size={13} /> Upload CSV
          </button>
          <button onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-1.5 px-3 py-2 text-xs font-medium">
            <Plus size={13} /> Add
          </button>
        </div>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-800/40 bg-rose-950/20 px-4 py-3">
          <span className="text-sm text-rose-300">{selected.size} selected</span>
          <button onClick={() => void handleBulkDelete()} disabled={bulkDeleting}
            className="flex items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-rose-500 disabled:opacity-40">
            <Trash2 size={12} />
            {bulkDeleting ? "Deleting…" : `Delete ${selected.size}`}
          </button>
          <button onClick={() => setSelected(new Set())}
            className="ml-auto text-xs text-zinc-500 hover:text-zinc-300">
            Clear selection
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="form-inline panel rounded-2xl p-4">
        <select value={filterAccount} onChange={(e) => { setFilterAccount(e.target.value); setPage(0); }} className="select-field min-w-[10rem] flex-1 sm:flex-none">
          <option value="">All accounts</option>
          {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <select value={filterCategory} onChange={(e) => { setFilterCategory(e.target.value); setPage(0); }} className="select-field min-w-[10rem] flex-1 sm:flex-none">
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input type="date" value={filterFrom} onChange={(e) => { setFilterFrom(e.target.value); setPage(0); }} className="input-field input-field--sm min-w-[9rem] flex-1 sm:flex-none" />
        <input type="date" value={filterTo} onChange={(e) => { setFilterTo(e.target.value); setPage(0); }} className="input-field input-field--sm min-w-[9rem] flex-1 sm:flex-none" />
        {(filterAccount || filterCategory || filterFrom || filterTo) && (
          <button onClick={() => { setFilterAccount(""); setFilterCategory(""); setFilterFrom(""); setFilterTo(""); setPage(0); }}
            className="btn-ghost inline-flex items-center gap-1.5 px-3 py-2 text-sm">
            <X size={11} /> Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-zinc-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="w-10 px-4 py-3">
                <input type="checkbox" checked={selected.size === sorted.length && sorted.length > 0}
                  onChange={toggleAll}
                  className="rounded border-zinc-600 bg-zinc-800 accent-teal-500 cursor-pointer" />
              </th>
              {(["transaction_date", "description", "category", "amount"] as SortKey[]).map((col) => (
                <th key={col}
                  onClick={() => handleSort(col)}
                  className="cursor-pointer select-none px-4 py-3 text-left text-xs font-medium text-zinc-500 hover:text-zinc-300">
                  <span className="flex items-center gap-1 capitalize">
                    {col === "transaction_date" ? "Date" : col}
                    <SortIcon col={col} />
                  </span>
                </th>
              ))}
              <th className="px-4 py-3 text-left text-xs font-medium text-zinc-500">Merchant</th>
              <th className="w-10 px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 bg-zinc-950">
            {loading
              ? Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>{Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-3.5 shimmer rounded" /></td>
                  ))}</tr>
                ))
              : sorted.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-sm text-zinc-600">
                      No transactions found. Adjust filters or upload a CSV.
                    </td>
                  </tr>
                )
              : sorted.map((tx) => (
                  <tr key={tx.id} className={["transition-colors hover:bg-zinc-900/60",
                    selected.has(tx.id) ? "bg-teal-950/20" : "",
                  ].join(" ")}>
                    <td className="px-4 py-3">
                      <input type="checkbox" checked={selected.has(tx.id)} onChange={() => toggleSelect(tx.id)}
                        className="rounded border-zinc-600 bg-zinc-800 accent-teal-500 cursor-pointer" />
                    </td>
                    <td className="px-4 py-3 text-zinc-400 tabular-nums whitespace-nowrap text-xs">
                      {formatDate(tx.transaction_date)}
                    </td>
                    <td className="max-w-[200px] px-4 py-3">
                      <p className="truncate text-zinc-200">{tx.description}</p>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={tx.category}
                        onChange={(e) => void handleCategoryChange(tx.id, e.target.value)}
                        className="select-field min-h-0 py-1 text-xs"
                      >
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>
                    <td className={["px-4 py-3 text-right tabular-nums font-medium whitespace-nowrap",
                      tx.amount < 0 ? "text-rose-400" : "text-emerald-400",
                    ].join(" ")}>
                      {tx.amount < 0 ? "−" : "+"}{formatCurrency(tx.amount)}
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-500">{tx.merchant ?? "—"}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => void handleDelete(tx.id)}
                        className="rounded p-1 text-zinc-700 transition-colors hover:text-rose-400">
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                ))
            }
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-zinc-500">Page {page + 1} of {totalPages} · {total.toLocaleString()} records</p>
          <div className="flex gap-2">
            <button disabled={page === 0} onClick={() => setPage(page - 1)}
              className="flex items-center gap-1 rounded-lg border border-zinc-800 px-3 py-1.5 text-zinc-400 hover:bg-zinc-900 disabled:opacity-30">
              <ChevronLeft size={14} /> Prev
            </button>
            <button disabled={page + 1 >= totalPages} onClick={() => setPage(page + 1)}
              className="flex items-center gap-1 rounded-lg border border-zinc-800 px-3 py-1.5 text-zinc-400 hover:bg-zinc-900 disabled:opacity-30">
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {showCreate && (
        <CreateModal accounts={accounts} onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); toast("Transaction saved"); loadData(); }} />
      )}
      {showUpload && (
        <UploadModal accounts={accounts} onClose={() => setShowUpload(false)}
          onUploaded={(n) => { setShowUpload(false); toast(`${n} transactions imported`); loadData(); }} />
      )}
    </div>
  );
}

// ── Create Modal ──────────────────────────────────────────────────────────────

function CreateModal({ accounts, onClose, onCreated }: {
  accounts: Account[]; onClose: () => void; onCreated: () => void;
}) {
  const [form, setForm] = useState({
    account_id: accounts[0]?.id ?? "", transaction_date: new Date().toISOString().slice(0, 10),
    description: "", amount: "", category: "Uncategorized", merchant: "", notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true); setError("");
    try {
      await api.createTransaction({ ...form, amount: parseFloat(form.amount),
        merchant: form.merchant || undefined, notes: form.notes || undefined });
      onCreated();
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); setSaving(false); }
  };

  return (
    <Modal title="Add Transaction" onClose={onClose}>
      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
        {error && <p className="text-sm text-rose-400">{error}</p>}
        {accounts.length === 0 && <p className="text-sm text-amber-400">Create an account first.</p>}
        <Field label="Account">
          <select value={form.account_id} onChange={(e) => setForm({ ...form, account_id: e.target.value })} className={inp} required>
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.institution})</option>)}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Date">
            <input type="date" value={form.transaction_date} onChange={(e) => setForm({ ...form, transaction_date: e.target.value })} className={inp} required />
          </Field>
          <Field label="Amount">
            <input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className={inp} placeholder="-12.50" required />
          </Field>
        </div>
        <Field label="Description">
          <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={inp} placeholder="e.g. Starbucks Coffee" required />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Category">
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className={inp}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Merchant">
            <input type="text" value={form.merchant} onChange={(e) => setForm({ ...form, merchant: e.target.value })} className={inp} placeholder="Optional" />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className={cancelBtn}>Cancel</button>
          <button type="submit" disabled={saving || !accounts.length} className={primaryBtn}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ── Upload Modal ──────────────────────────────────────────────────────────────

function UploadModal({ accounts, onClose, onUploaded }: {
  accounts: Account[]; onClose: () => void; onUploaded: (n: number) => void;
}) {
  const [accountId, setAccountId] = useState(accounts[0]?.id ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ created: number; errors: string[] } | null>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!file || !accountId) return;
    setUploading(true); setError("");
    try {
      const res = await api.uploadCsv(file, accountId);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally { setUploading(false); }
  };

  if (result) return (
    <Modal title="Upload Complete" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <div className="rounded-xl bg-emerald-500/10 p-4 text-sm text-emerald-400">
          ✓ {result.created} transactions imported.
        </div>
        {result.errors.length > 0 && (
          <div className="rounded-xl bg-rose-500/10 p-4">
            <p className="mb-1 text-sm text-rose-400">{result.errors.length} errors:</p>
            <ul className="list-disc pl-4 text-xs text-rose-300">{result.errors.slice(0, 10).map((e, i) => <li key={i}>{e}</li>)}</ul>
          </div>
        )}
        <div className="flex justify-end">
          <button onClick={() => onUploaded(result.created)} className={primaryBtn}>Done</button>
        </div>
      </div>
    </Modal>
  );

  return (
    <Modal title="Upload CSV" onClose={onClose}>
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-rose-400">{error}</p>}
        {!accounts.length && <p className="text-sm text-amber-400">Create an account first.</p>}
        <Field label="Account">
          <select value={accountId} onChange={(e) => setAccountId(e.target.value)} className={inp}>
            {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.institution})</option>)}
          </select>
        </Field>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}
          onClick={() => fileRef.current?.click()}
          className={["flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed p-8 text-center transition-colors",
            dragging ? "border-teal-500 bg-teal-500/10" : "border-zinc-700 bg-zinc-800/50 hover:border-zinc-600",
          ].join(" ")}
        >
          <Upload size={22} className="text-zinc-500" />
          {file ? <p className="text-sm text-zinc-300">{file.name}</p> : (
            <>
              <p className="text-sm text-zinc-400">Drop CSV or <span className="link-accent">click to browse</span></p>
              <p className="text-xs text-zinc-600">Required: <code className="text-zinc-500">date, description, amount</code></p>
            </>
          )}
          <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }} />
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className={cancelBtn}>Cancel</button>
          <button onClick={() => void handleUpload()} disabled={!file || !accountId || uploading || !accounts.length} className={primaryBtn}>
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </div>
      </div>
    </Modal>
  );
}

// ── Shared ────────────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300"><X size={16} /></button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-zinc-400">{label}</label>
      {children}
    </div>
  );
}
const inp = "w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500/40";
const primaryBtn = "rounded-lg btn-primary px-4 py-2 text-sm font-medium text-white transition-colors  disabled:opacity-40";
const cancelBtn = "rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200";
