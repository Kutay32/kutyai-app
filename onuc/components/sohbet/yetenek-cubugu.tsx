"use client";

import { Sparkles, Wrench } from "lucide-react";

import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";

export type YetenekCubuguOzellikleri = {
  ragAcik: boolean;
  aracAcik: boolean;
  /** Yanıt akarken yetenekler değiştirilemez. */
  devreDisi: boolean;
  onRag: (acik: boolean) => void;
  onArac: (acik: boolean) => void;
};

/** Anahtar düğmelerinin ortak sınıfları; açıkken koyu yüzey kullanılır. */
function anahtarSinifi(acik: boolean): string {
  return cn(
    "inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-[13px] transition-colors focus:border-neutral-900 focus:ring-0 disabled:cursor-not-allowed disabled:opacity-50",
    acik
      ? "border-neutral-900 bg-neutral-900 text-white"
      : "border-neutral-200 bg-white text-neutral-500 hover:border-neutral-900 hover:text-neutral-900",
  );
}

/** Besteci üstü yetenek anahtarları: bilgi tabanı ve araç panelleri. */
export function YetenekCubugu({
  ragAcik,
  aracAcik,
  devreDisi,
  onRag,
  onArac,
}: YetenekCubuguOzellikleri) {
  const { t } = useDil();

  return (
    <div
      className="flex flex-wrap items-center gap-1"
      role="group"
      aria-label={t("sohbet.yetenek.etiket")}
    >
      <button
        type="button"
        aria-pressed={ragAcik}
        disabled={devreDisi}
        onClick={() => onRag(!ragAcik)}
        className={anahtarSinifi(ragAcik)}
      >
        <Sparkles aria-hidden className="size-3.5" />
        {t("sohbet.rag.etiket")}
      </button>
      <button
        type="button"
        aria-pressed={aracAcik}
        disabled={devreDisi}
        onClick={() => onArac(!aracAcik)}
        className={anahtarSinifi(aracAcik)}
      >
        <Wrench aria-hidden className="size-3.5" />
        {t("sohbet.arac.etiket")}
      </button>
    </div>
  );
}
