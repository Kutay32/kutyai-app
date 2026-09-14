"use client";

import { useId } from "react";

import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import { DIL_ADLARI, type Dil } from "@/lib/sozluk";

/** Dil seçici; üst barda kullanılır (spec §10.2). */
export function DilSecici({ className }: { className?: string }) {
  const { dil, diller, dilDegistir, t } = useDil();
  const seciciId = useId();

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <label htmlFor={seciciId} className="text-xs text-neutral-500">
        {t("genel.dil")}
      </label>
      <select
        id={seciciId}
        value={dil}
        onChange={(olay) => dilDegistir(olay.target.value as Dil)}
        className={cn(
          "h-8 rounded-md border border-neutral-300 bg-white px-2 text-sm text-neutral-800 transition-colors",
          "focus:border-neutral-900 focus:ring-0 focus:outline-none",
        )}
      >
        {diller.map((kod) => (
          <option key={kod} value={kod}>
            {DIL_ADLARI[kod]}
          </option>
        ))}
      </select>
    </div>
  );
}
