"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";

export type TerminalLogProps = {
  satirlar: string[];
  otomatikKaydir: boolean;
  className?: string;
};

/** Terminal görünümlü günlük alanı; otomatik kaydırma açıkken sona sabitlenir. */
export function TerminalLog({ satirlar, otomatikKaydir, className }: TerminalLogProps) {
  const kutu = useRef<HTMLDivElement>(null);
  const { t } = useDil();

  useEffect(() => {
    const alan = kutu.current;
    if (!alan || !otomatikKaydir) return;
    alan.scrollTop = alan.scrollHeight;
  }, [satirlar, otomatikKaydir]);

  return (
    <div
      ref={kutu}
      role="log"
      aria-label={t("bdm.gunluk.baslik")}
      aria-live="polite"
      className={cn(
        "h-96 overflow-y-auto rounded-lg border border-neutral-200 bg-neutral-50 p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap text-neutral-800",
        className,
      )}
    >
      {satirlar.length === 0 ? (
        <p className="font-sans text-neutral-500">{t("bdm.gunluk.bos")}</p>
      ) : (
        satirlar.map((satir, sira) => (
          // Günlük satırları sıralı ve tekrar edebilir; anahtar olarak sıra kullanılır.
          <div key={sira}>{satir}</div>
        ))
      )}
    </div>
  );
}
