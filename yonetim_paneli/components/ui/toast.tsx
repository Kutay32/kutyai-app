"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from "lucide-react";

import { cn } from "@/lib/cn";

export type ToastTone = "info" | "success" | "warning" | "danger";

type ToastItem = {
  id: number;
  message: string;
  tone: ToastTone;
};

type ToastContextValue = {
  showToast: (message: string, tone?: ToastTone) => void;
};

const TONE: Record<ToastTone, { kutu: string; ikon: ReactNode }> = {
  info: { kutu: "border-sky-300 bg-sky-50 text-sky-900", ikon: <Info aria-hidden className="size-4" /> },
  success: {
    kutu: "border-emerald-300 bg-emerald-50 text-emerald-900",
    ikon: <CircleCheck aria-hidden className="size-4" />,
  },
  warning: {
    kutu: "border-amber-300 bg-amber-50 text-amber-900",
    ikon: <TriangleAlert aria-hidden className="size-4" />,
  },
  danger: {
    kutu: "border-rose-300 bg-rose-50 text-rose-900",
    ikon: <CircleAlert aria-hidden className="size-4" />,
  },
};

const ToastContext = createContext<ToastContextValue | null>(null);

/** Kısa ömürlü bilgilendirme gösterir. `ToastProvider` altında çağrılmalıdır. */
export function useToast(): ToastContextValue {
  const deger = useContext(ToastContext);
  if (!deger) throw new Error("useToast yalnızca ToastProvider içinde kullanılabilir.");
  return deger;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const sayac = useRef(0);

  const kapat = useCallback((id: number) => {
    setItems((onceki) => onceki.filter((oge) => oge.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, tone: ToastTone = "info") => {
      sayac.current += 1;
      const id = sayac.current;
      setItems((onceki) => [...onceki, { id, message, tone }]);
      window.setTimeout(() => kapat(id), 5000);
    },
    [kapat],
  );

  const deger = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={deger}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed right-4 bottom-4 z-[60] flex w-full max-w-sm flex-col gap-2"
      >
        {items.map((oge) => (
          <div
            key={oge.id}
            className={cn(
              "pointer-events-auto flex items-start gap-2 rounded-lg border p-4 text-sm shadow-sm",
              TONE[oge.tone].kutu,
            )}
          >
            <span className="mt-0.5 shrink-0">{TONE[oge.tone].ikon}</span>
            <p className="flex-1">{oge.message}</p>
            <button
              type="button"
              onClick={() => kapat(oge.id)}
              aria-label="Bildirimi kapat"
              className="rounded-md p-0.5 transition-colors hover:bg-black/5 focus:outline-none focus:border-neutral-900 focus:ring-0"
            >
              <X aria-hidden className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
