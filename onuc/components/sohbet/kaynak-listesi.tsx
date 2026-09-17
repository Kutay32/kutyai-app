"use client";

import { BookOpen } from "lucide-react";

import { sayiBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import type { SohbetKaynagi } from "@/lib/sohbet";

export type KaynakListesiOzellikleri = {
  kaynaklar: SohbetKaynagi[];
};

/** Asistan yanıtının dayandığı bilgi tabanı parçaları (`kaynaklar`). */
export function KaynakListesi({ kaynaklar }: KaynakListesiOzellikleri) {
  const { dil, t } = useDil();
  if (kaynaklar.length === 0) return null;

  return (
    <section
      aria-label={t("sohbet.kaynak.baslik")}
      className="rounded-lg border border-neutral-200 bg-white p-3"
    >
      <h4 className="flex items-center gap-1.5 text-[13px] font-medium text-neutral-900">
        <BookOpen aria-hidden className="size-3.5" />
        {t("sohbet.kaynak.baslik")}
      </h4>
      <ul className="mt-2 flex flex-col gap-1">
        {kaynaklar.map((kaynak) => (
          <li
            key={`${kaynak.belge_id}-${kaynak.sira}`}
            className="flex flex-wrap items-baseline justify-between gap-x-3 text-[13px]"
          >
            <span className="min-w-0 truncate text-neutral-900">{kaynak.belge_ad}</span>
            <span className="shrink-0 text-neutral-500">
              {/* Sunucu `sira`yı sıfırdan verir; ekranda 1'den numaralanır (panel deseni). */}
              {t("sohbet.kaynak.parca", { sira: kaynak.sira + 1 })} ·{" "}
              {t("sohbet.kaynak.skor", {
                skor: sayiBicimle(Math.round(kaynak.skor * 100), dil),
              })}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
