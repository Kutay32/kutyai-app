"use client";

import { useId } from "react";

import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import type { BdmOzet } from "@/lib/sohbet";

export type ModelSeciciOzellikleri = {
  modeller: BdmOzet[];
  seciliId: number | null;
  /** Üretim sürerken model değiştirilemez. */
  devreDisi?: boolean;
  onSec: (bdmId: number) => void;
};

/** Sohbet modeli seçici; seçim `localStorage`'da saklanır (ekran yönetir). */
export function ModelSecici({
  modeller,
  seciliId,
  devreDisi = false,
  onSec,
}: ModelSeciciOzellikleri) {
  const alanId = useId();
  const { t } = useDil();

  return (
    <div className="flex min-w-0 items-center gap-2">
      <label htmlFor={alanId} className="text-[13px] font-medium whitespace-nowrap text-neutral-900">
        {t("sohbet.model.etiket")}
      </label>
      <select
        id={alanId}
        value={seciliId ?? ""}
        disabled={devreDisi}
        onChange={(olay) => onSec(Number(olay.target.value))}
        className={cn(
          "h-9 min-w-0 max-w-[16rem] truncate rounded-lg border border-neutral-200 bg-white px-2 text-[13px] text-neutral-900",
          "focus:border-neutral-900 focus:ring-0 focus:outline-none",
          "disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:text-neutral-500",
        )}
      >
        {seciliId === null ? (
          <option value="" disabled>
            {t("sohbet.model.secin")}
          </option>
        ) : null}
        {modeller.map((model) => (
          <option key={model.id} value={model.id}>
            {model.gorunen_ad}
          </option>
        ))}
      </select>
    </div>
  );
}
