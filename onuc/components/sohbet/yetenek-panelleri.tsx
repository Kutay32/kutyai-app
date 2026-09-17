"use client";

import { RefreshCw } from "lucide-react";

import { Buton } from "@/components/ui/buton";
import { Yukleniyor } from "@/components/ui/yukleniyor";
import { sayiBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { KAYNAK_ANAHTARI, type BelgeOzeti } from "@/lib/rag";
import type { AracSecenegi } from "@/lib/sohbet";

export type BelgeSecimiOzellikleri = {
  belgeler: BelgeOzeti[] | null;
  seciliIdler: number[];
  yukleniyor: boolean;
  hata: string | null;
  devreDisi: boolean;
  onDegistir: (belgeId: number) => void;
  onYenile: () => void;
};

/** Bilgi tabanı belgeleri: seçim yapılmazsa tüm belgeler taranır. */
export function BelgeSecimi({
  belgeler,
  seciliIdler,
  yukleniyor,
  hata,
  devreDisi,
  onDegistir,
  onYenile,
}: BelgeSecimiOzellikleri) {
  const { dil, t } = useDil();

  return (
    <div className="rounded-lg border border-neutral-200 p-3">
      <p className="text-[13px] text-neutral-500">{t("sohbet.rag.tumu")}</p>
      {hata ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <p role="alert" className="text-[13px] text-rose-600">
            {hata}
          </p>
          <Buton tur="ikincil" boyut="kucuk" disabled={devreDisi} onClick={onYenile}>
            <RefreshCw aria-hidden className="size-3.5" />
            {t("sohbet.rag.yenile")}
          </Buton>
        </div>
      ) : yukleniyor ? (
        <div className="mt-2">
          <Yukleniyor etiket={t("sohbet.rag.yukleniyor")} boyut="kucuk" />
        </div>
      ) : (belgeler?.length ?? 0) === 0 ? (
        <p className="mt-2 text-[13px] text-neutral-500">{t("sohbet.rag.belge.yok")}</p>
      ) : (
        <ul className="mt-2 flex max-h-44 flex-col gap-1 overflow-y-auto">
          {(belgeler ?? []).map((belge) => (
            <li key={belge.id}>
              <label className="flex cursor-pointer items-center gap-2 rounded-md px-1 py-1 text-[13px] text-neutral-900 hover:bg-neutral-50">
                <input
                  type="checkbox"
                  className="size-3.5 accent-neutral-900"
                  checked={seciliIdler.includes(belge.id)}
                  disabled={devreDisi}
                  onChange={() => onDegistir(belge.id)}
                />
                <span className="min-w-0 flex-1 truncate">{belge.ad}</span>
                <span className="shrink-0 text-neutral-500">
                  {t(KAYNAK_ANAHTARI[belge.kaynak])} ·{" "}
                  {t("bilgi.parca.sayisi", { sayi: sayiBicimle(belge.parca_sayisi, dil) })}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export type AracSecimiOzellikleri = {
  araclar: AracSecenegi[] | null;
  seciliSluglar: string[];
  yukleniyor: boolean;
  hata: string | null;
  devreDisi: boolean;
  onDegistir: (slug: string) => void;
  onYenile: () => void;
};

/** Etkin araçlar: seçilenler `arac_sluglari` olarak gönderilir. */
export function AracSecimi({
  araclar,
  seciliSluglar,
  yukleniyor,
  hata,
  devreDisi,
  onDegistir,
  onYenile,
}: AracSecimiOzellikleri) {
  const { t } = useDil();

  return (
    <div className="rounded-lg border border-neutral-200 p-3">
      <p className="text-[13px] text-neutral-500">{t("sohbet.arac.aciklama")}</p>
      <p className="text-[13px] text-neutral-500">{t("sohbet.arac.tumu")}</p>
      {hata ? (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <p role="alert" className="text-[13px] text-rose-600">
            {hata}
          </p>
          <Buton tur="ikincil" boyut="kucuk" disabled={devreDisi} onClick={onYenile}>
            <RefreshCw aria-hidden className="size-3.5" />
            {t("sohbet.arac.yenile")}
          </Buton>
        </div>
      ) : yukleniyor ? (
        <div className="mt-2">
          <Yukleniyor etiket={t("sohbet.arac.yukleniyor")} boyut="kucuk" />
        </div>
      ) : (araclar?.length ?? 0) === 0 ? (
        <p className="mt-2 text-[13px] text-neutral-500">{t("sohbet.arac.yok")}</p>
      ) : (
        <ul className="mt-2 flex max-h-44 flex-col gap-1 overflow-y-auto">
          {(araclar ?? []).map((arac) => (
            <li key={arac.id}>
              <label className="flex cursor-pointer items-center gap-2 rounded-md px-1 py-1 text-[13px] text-neutral-900 hover:bg-neutral-50">
                <input
                  type="checkbox"
                  className="size-3.5 accent-neutral-900"
                  checked={seciliSluglar.includes(arac.slug)}
                  disabled={devreDisi}
                  onChange={() => onDegistir(arac.slug)}
                />
                <span className="min-w-0 flex-1 truncate">{arac.ad}</span>
                <span className="shrink-0 font-mono text-[11px] text-neutral-500">{arac.slug}</span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
