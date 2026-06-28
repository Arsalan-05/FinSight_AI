"use client";

import { CheckCircle, Info, XCircle } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useId,
  useState,
} from "react";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastCtx {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastCtx>({ toast: () => {} });

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const baseId = useId();

  const toast = useCallback(
    (message: string, type: ToastType = "success") => {
      const id = `${baseId}-${Date.now()}`;
      setItems((prev) => [...prev, { id, message, type }]);
      setTimeout(
        () => setItems((prev) => prev.filter((t) => t.id !== id)),
        3500,
      );
    },
    [baseId],
  );

  const styles: Record<ToastType, string> = {
    success: "border-emerald-700/60 bg-emerald-950/90 text-emerald-300",
    error: "border-red-700/60 bg-red-950/90 text-red-300",
    info: "border-zinc-700 bg-zinc-900/90 text-zinc-300",
  };

  const icons: Record<ToastType, React.ReactNode> = {
    success: <CheckCircle size={15} className="shrink-0 text-emerald-400" />,
    error: <XCircle size={15} className="shrink-0 text-red-400" />,
    info: <Info size={15} className="shrink-0 text-zinc-400" />,
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-[200] flex flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={[
              "flex items-center gap-2.5 rounded-xl border px-4 py-3 text-sm shadow-2xl backdrop-blur",
              "animate-in slide-in-from-right-4 fade-in duration-200",
              styles[item.type],
            ].join(" ")}
          >
            {icons[item.type]}
            <span>{item.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
