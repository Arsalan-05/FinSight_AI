import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-zinc-400">
      <Loader2 className="h-8 w-8 animate-spin text-indigo-400" aria-hidden />
      <p className="text-sm">Loading FinSight…</p>
    </div>
  );
}
