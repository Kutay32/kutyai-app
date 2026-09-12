"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";

export type BildirimTuru = "basari" | "hata" | "bilgi";

export type BildirimGirdisi = {
  tur?: BildirimTuru;
  baslik?: string;
  mesaj: string;
};

type BildirimKaydi = Required<Pick<BildirimGirdisi, "tur" | "mesaj">> &
  Pick<BildirimGirdisi, "baslik"> & { id: number };

type BildirimBaglami = {
  /** Kısa süreli bildirim (toast) gösterir; 4 sn sonra kendiliğinden kapanır. */
  goster: (bildirim: BildirimGirdisi) => void;
};

const Baglam = createContext<BildirimBaglami | null>(null);

const TUR_SINIFLARI: Record<BildirimTuru, string> = {
  basari: "border-green-200 text-green-800",
  hata: "border-rose-200 text-rose-700",
  bilgi: "border-neutral-200 text-neutral-900",
};

function TurSimgesi({ tur }: { tur: BildirimTuru }) {
  const sinif = "mt-0.5 size-4 shrink-0";
  if (tur === "basari") return <CheckCircle2 aria-hidden className={sinif} />;
  if (tur === "hata") return <XCircle aria-hidden className={sinif} />;
  return <Info aria-hidden className={sinif} />;
}

export function BildirimSaglayici({ children }: { children: React.ReactNode }) {
  const [kayitlar, setKayitlar] = useState<BildirimKaydi[]>([]);
  const sayac = useRef(0);

  const kapat = useCallback((id: number) => {
    setKayitlar((mevcut) => mevcut.filter((kayit) => kayit.id !== id));
  }, []);

  const goster = useCallback(
    (bildirim: BildirimGirdisi) => {
      const id = ++sayac.current;
      const kayit: BildirimKaydi = { id, tur: bildirim.tur ?? "bilgi", mesaj: bildirim.mesaj };
      if (bildirim.baslik) kayit.baslik = bildirim.baslik;
      setKayitlar((mevcut) => [...mevcut, kayit].slice(-3));
      window.setTimeout(() => kapat(id), 4000);
    },
    [kapat],
  );

  const baglam = useMemo(() => ({ goster }), [goster]);

  return (
    <Baglam.Provider value={baglam}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-end gap-2 p-4"
      >
        {kayitlar.map((kayit) => (
          <div
            key={kayit.id}
            className={cn(
              "pointer-events-auto flex w-full max-w-sm items-start gap-2 rounded-lg border bg-white p-4 shadow-none",
              TUR_SINIFLARI[kayit.tur],
            )}
          >
            <TurSimgesi tur={kayit.tur} />
            <div className="flex-1">
              {kayit.baslik ? <p className="text-[13px] font-medium">{kayit.baslik}</p> : null}
              <p className="text-[13px] text-neutral-600">{kayit.mesaj}</p>
            </div>
            <button
              type="button"
              onClick={() => kapat(kayit.id)}
              aria-label="Bildirimi kapat"
              className="rounded-md border border-transparent p-1 text-neutral-400 transition-colors hover:border-neutral-200 hover:text-neutral-900 focus:border-neutral-900 focus:ring-0"
            >
              <X aria-hidden className="size-3.5" />
            </button>
          </div>
        ))}
      </div>
    </Baglam.Provider>
  );
}

export function useBildirim(): BildirimBaglami {
  const baglam = useContext(Baglam);
  if (!baglam) throw new Error("useBildirim yalnız BildirimSaglayici içinde kullanılabilir.");
  return baglam;
}
