"use client";

import { forwardRef } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";

export type YukleniyorOzellikleri = React.HTMLAttributes<HTMLSpanElement> & {
  /** Ekran okuyucuya ve görünür metne yazılan etiket; verilmezse katalogdan gelir. */
  etiket?: string;
  boyut?: "kucuk" | "orta" | "buyuk";
};

const BOYUT_SINIFLARI = {
  kucuk: "size-4",
  orta: "size-5",
  buyuk: "size-8",
} as const;

/** Dönen gösterge; `prefers-reduced-motion` tercihinde dönme durur. */
export const Yukleniyor = forwardRef<HTMLSpanElement, YukleniyorOzellikleri>(function Yukleniyor(
  { className, etiket, boyut = "orta", ...kalan },
  ref,
) {
  const { t } = useDil();

  return (
    <span
      ref={ref}
      role="status"
      aria-live="polite"
      className={cn("inline-flex items-center gap-2 text-neutral-500", className)}
      {...kalan}
    >
      <Loader2 aria-hidden className={cn("animate-spin", BOYUT_SINIFLARI[boyut])} />
      <span className="text-[13px]">{etiket ?? t("genel.yukleniyor")}</span>
    </span>
  );
});

export type YukleniyorDurumuOzellikleri = React.HTMLAttributes<HTMLDivElement> & {
  etiket?: string;
};

/** Kart/panel ortasında tek başına duran yükleme durumu. */
export const YukleniyorDurumu = forwardRef<HTMLDivElement, YukleniyorDurumuOzellikleri>(
  function YukleniyorDurumu({ className, etiket, ...kalan }, ref) {
    return (
      <div ref={ref} className={cn("flex items-center justify-center py-10", className)} {...kalan}>
        <Yukleniyor etiket={etiket} />
      </div>
    );
  },
);
