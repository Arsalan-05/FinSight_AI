"use client";

import { Download, X } from "lucide-react";
import { useEffect, useState } from "react";

const DISMISS_KEY = "finsight-pwa-dismissed";

export function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem(DISMISS_KEY)) return;
    if (window.matchMedia("(display-mode: standalone)").matches) return;

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  };

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    dismiss();
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-6 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 md:left-auto md:right-8 md:translate-x-0">
      <div className="panel flex items-center gap-4 rounded-2xl border-[var(--border-glow)] p-4 shadow-xl">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
          <Download size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[var(--foreground)]">Install FinSight</p>
          <p className="text-xs text-[var(--muted)]">Add to your home screen for quick access.</p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button type="button" onClick={() => void install()} className="btn-primary rounded-lg px-3 py-1.5 text-xs">
            Install
          </button>
          <button
            type="button"
            onClick={dismiss}
            className="rounded-lg p-1.5 text-[var(--muted)] hover:bg-[var(--surface)]"
            aria-label="Dismiss"
          >
            <X size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

declare global {
  interface WindowEventMap {
    beforeinstallprompt: BeforeInstallPromptEvent;
  }
}
