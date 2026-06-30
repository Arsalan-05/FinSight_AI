"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen items-center justify-center bg-zinc-950 p-6 text-zinc-100">
        <div className="glass max-w-md rounded-2xl border border-zinc-800 p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-rose-500/10 text-rose-400">
            <AlertTriangle size={22} />
          </div>
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="mt-2 text-sm text-zinc-400">
            FinSight hit an unexpected error. Try refreshing — your data is safe.
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="btn-primary mt-6 inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium"
          >
            <RefreshCw size={14} />
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
