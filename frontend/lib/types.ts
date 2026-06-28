export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface Account {
  id: string;
  user_id: string;
  name: string;
  institution: string;
  account_type: "checking" | "savings" | "credit";
  created_at: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  transaction_date: string;
  description: string;
  amount: number;
  category: string;
  merchant: string | null;
  notes: string | null;
  created_at: string;
}

export interface TransactionList {
  total: number;
  items: Transaction[];
}

export interface SearchResponse {
  results: Transaction[];
  query: string;
  k: number;
  embedding_enabled: boolean;
}

export interface HealthResponse {
  status: string;
  environment: string;
}

export const CATEGORY_COLORS: Record<string, string> = {
  Dining: "#f59e0b",
  Groceries: "#22c55e",
  Transport: "#3b82f6",
  Housing: "#8b5cf6",
  Shopping: "#ec4899",
  Subscriptions: "#6366f1",
  Healthcare: "#14b8a6",
  Income: "#10b981",
  Entertainment: "#f97316",
  Utilities: "#64748b",
  Uncategorized: "#6b7280",
};

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] ?? "#6b7280";
}
