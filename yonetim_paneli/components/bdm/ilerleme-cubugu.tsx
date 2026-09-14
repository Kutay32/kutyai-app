"use client";

import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";

export type IlerlemeCubuguProps = {
  yuzde: number;
  mesaj?: string;
  className?: string;
};

/** Düz yüzeyli ilerleme çubuğu (gradyan yok); ekran okuyucuya yüzdeyi bildirir. */
export function IlerlemeCubugu({ yuzde, mesaj, className }: IlerlemeCubuguProps) {
  const { t } = useDil();
  const oran = Math.max(0, Math.min(100, yuzde));

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={oran}
        aria-label={t("bdm.ilerleme.etiket")}
        className="h-2 w-full overflow-hidden rounded-md border border-neutral-200 bg-neutral-100"
      >
        <div
          className="h-full bg-neutral-900 transition-[width]"
          style={{ width: `${oran}%` }}
        />
      </div>
      <p className="text-xs text-neutral-600" role="status">
        {mesaj
          ? t("bdm.ilerleme.satir", { yuzde: oran, mesaj })
          : t("bdm.ilerleme.yuzde", { yuzde: oran })}
      </p>
    </div>
  );
}
