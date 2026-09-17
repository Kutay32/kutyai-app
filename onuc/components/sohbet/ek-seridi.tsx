"use client";

import { useId, useRef } from "react";
import { Paperclip, X } from "lucide-react";

import { Buton } from "@/components/ui/buton";
import { Yukleniyor } from "@/components/ui/yukleniyor";
import { boyutBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import type { DosyaOzeti } from "@/lib/dosyalar";

export type EkSeridiOzellikleri = {
  /** Sohbete eklenecek dosyalar (`dosya_idleri` olarak gönderilir). */
  ekler: DosyaOzeti[];
  yukleniyor: boolean;
  /** Yükleme hatası; sunucunun Türkçe gerekçesi ya da katalog metni. */
  hata: string | null;
  /** Yanıt akarken ek değiştirilemez. */
  devreDisi: boolean;
  onEkle: (dosya: File) => void;
  onKaldir: (dosyaId: number) => void;
};

/** Sohbet eki şeridi: dosya seçme düğmesi ve yüklenen eklerin çipleri. */
export function EkSeridi({
  ekler,
  yukleniyor,
  hata,
  devreDisi,
  onEkle,
  onKaldir,
}: EkSeridiOzellikleri) {
  const { dil, t } = useDil();
  const alanId = useId();
  const girdiRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={girdiRef}
          id={alanId}
          type="file"
          className="peer sr-only"
          disabled={devreDisi || yukleniyor}
          onChange={(olay) => {
            const dosya = olay.target.files?.[0];
            // Aynı dosya ikinci kez seçilebilsin diye girdi her seferinde sıfırlanır.
            olay.target.value = "";
            if (dosya) onEkle(dosya);
          }}
        />
        <label
          htmlFor={alanId}
          className="inline-flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-neutral-200 bg-white px-3 text-[13px] font-medium text-neutral-900 transition-colors hover:border-neutral-900 peer-focus-visible:border-neutral-900 peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
        >
          <Paperclip aria-hidden className="size-3.5" />
          {t("sohbet.ek.ekle")}
        </label>
        {yukleniyor ? <Yukleniyor etiket={t("sohbet.ek.yukleniyor")} boyut="kucuk" /> : null}
        {ekler.map((dosya) => (
          <span
            key={dosya.id}
            className="inline-flex max-w-[16rem] items-center gap-1 rounded-md border border-neutral-200 py-1 pr-1 pl-2 text-[13px] text-neutral-600"
          >
            <span className="truncate">{dosya.ad}</span>
            <span className="shrink-0 text-neutral-400">{boyutBicimle(dosya.boyut, dil)}</span>
            <Buton
              tur="hayalet"
              boyut="kucuk"
              className="h-5 px-1"
              disabled={devreDisi}
              onClick={() => onKaldir(dosya.id)}
              aria-label={t("sohbet.ek.kaldir", { ad: dosya.ad })}
            >
              <X aria-hidden className="size-3.5" />
            </Buton>
          </span>
        ))}
      </div>
      {hata ? (
        <p role="alert" className="px-1 text-[13px] text-rose-600">
          {hata}
        </p>
      ) : null}
    </div>
  );
}
