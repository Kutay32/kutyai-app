"use client";

import { Plus, Search } from "lucide-react";

import { Buton } from "@/components/ui/buton";
import { kisaTarihBicimle } from "@/lib/bicim";
import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import type { KonusmaOzeti } from "@/lib/sohbet";

import { KonusmaIskeleti } from "./durum-gorunumleri";

export type KonusmaListesiOzellikleri = {
  /** Aramadan geçmiş kayıtlar. */
  konusmalar: KonusmaOzeti[];
  toplam: number;
  seciliId: number | null;
  arama: string;
  yukleniyor: boolean;
  onArama: (deger: string) => void;
  onSec: (konusmaId: number) => void;
  onYeni: () => void;
};

/** Sol sütun: konuşma arama, liste ve `Yeni sohbet` (mobilde çekmece içinde). */
export function KonusmaListesi({
  konusmalar,
  toplam,
  seciliId,
  arama,
  yukleniyor,
  onArama,
  onSec,
  onYeni,
}: KonusmaListesiOzellikleri) {
  const { dil, t } = useDil();

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-3">
      <Buton tur="ikincil" boyut="kucuk" onClick={onYeni} className="w-full justify-center">
        <Plus aria-hidden className="size-3.5" />
        {t("sohbet.liste.yeni")}
      </Buton>

      <div className="relative">
        <Search
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-neutral-400"
        />
        <input
          type="search"
          value={arama}
          onChange={(olay) => onArama(olay.target.value)}
          aria-label={t("sohbet.liste.ara")}
          placeholder={t("sohbet.liste.ara")}
          className="h-9 w-full rounded-lg border border-neutral-200 bg-white pr-3 pl-8 text-[13px] text-neutral-900 placeholder:text-neutral-400 focus:border-neutral-900 focus:ring-0 focus:outline-none"
        />
      </div>

      <p className="px-1 text-[11px] text-neutral-500" role="status">
        {toplam === 0
          ? t("sohbet.liste.bos")
          : arama.trim()
            ? t("sohbet.liste.suzulmus", { gosterilen: konusmalar.length, toplam })
            : t("sohbet.liste.toplam", { toplam })}
      </p>

      <nav aria-label={t("sohbet.liste.baslik")} className="min-h-0 flex-1 overflow-y-auto">
        {yukleniyor ? (
          <KonusmaIskeleti />
        ) : konusmalar.length === 0 ? (
          <p className="px-1 text-[13px] text-neutral-500">
            {toplam === 0 ? t("sohbet.liste.ilk") : t("sohbet.liste.eslesme.yok")}
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {konusmalar.map((konusma) => {
              const etkin = konusma.id === seciliId;
              return (
                <li key={konusma.id}>
                  <button
                    type="button"
                    onClick={() => onSec(konusma.id)}
                    aria-current={etkin ? "true" : undefined}
                    className={cn(
                      "w-full rounded-lg border px-3 py-2 text-left transition-colors focus:border-neutral-900 focus:ring-0",
                      etkin
                        ? "border-neutral-900 bg-neutral-50"
                        : "border-transparent hover:border-neutral-200 hover:bg-neutral-50",
                    )}
                  >
                    <span className="block truncate text-[13px] font-medium text-neutral-900">
                      {konusma.baslik}
                    </span>
                    <span className="mt-0.5 flex items-center justify-between gap-2 text-[11px] text-neutral-500">
                      <span className="truncate">{konusma.bdm_ad}</span>
                      <span className="shrink-0">
                        {kisaTarihBicimle(konusma.guncellenme, dil)} · {konusma.mesaj_sayisi}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </div>
  );
}
