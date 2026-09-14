"use client";

import { memo } from "react";
import { RefreshCw } from "lucide-react";

import { Buton } from "@/components/ui/buton";
import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import type { GorunumMesaji } from "@/lib/sohbet";

import { MarkdownGorunumu } from "./markdown-gorunumu";

export type MesajBaloncuguOzellikleri = {
  mesaj: GorunumMesaji;
  /** Listenin son mesajı mı (yanıt eylemleri yalnız burada gösterilir). */
  sonMu: boolean;
  /** Herhangi bir yanıt akmakta mı. */
  gonderiliyor: boolean;
  onYenidenUret: () => void;
};

/**
 * Tek mesaj baloncuğu: kullanıcı sağda koyu, asistan solda açık yüzeyde.
 *
 * `memo` ile sarılıdır: akış sırasında yalnız içeriği değişen baloncuk yeniden
 * çizilir, geçmiş mesajların markdown'ı yeniden ayrıştırılmaz.
 */
export const MesajBaloncugu = memo(function MesajBaloncugu({
  mesaj,
  sonMu,
  gonderiliyor,
  onYenidenUret,
}: MesajBaloncuguOzellikleri) {
  const { t } = useDil();
  const kullaniciMi = mesaj.rol === "kullanici";
  const eylemlerGorunur = sonMu && !gonderiliyor;

  return (
    <article className={cn("flex", kullaniciMi ? "justify-end" : "justify-start")}>
      <div className={cn("flex max-w-[85%] flex-col gap-1", kullaniciMi && "items-end")}>
        <div
          aria-live={mesaj.akisHalinde ? "polite" : undefined}
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm break-words",
            kullaniciMi
              ? "bg-neutral-900 whitespace-pre-wrap text-white"
              : "border border-neutral-200 bg-neutral-50 text-neutral-900",
          )}
        >
          {kullaniciMi ? (
            mesaj.icerik
          ) : (
            <>
              {mesaj.icerik ? <MarkdownGorunumu icerik={mesaj.icerik} /> : null}
              {mesaj.akisHalinde ? (
                <span
                  aria-hidden
                  className="mt-1 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-neutral-400 align-middle"
                />
              ) : null}
              {!mesaj.icerik && mesaj.akisHalinde ? (
                <p className="text-sm text-neutral-500" role="status">
                  {t("sohbet.mesaj.hazirlaniyor")}
                </p>
              ) : null}
            </>
          )}
        </div>

        {mesaj.durduruldu ? (
          <p className="px-1 text-[11px] text-neutral-500">{t("sohbet.mesaj.durduruldu")}</p>
        ) : null}
        {mesaj.hatali ? (
          <p className="px-1 text-[11px] text-rose-600">{t("sohbet.mesaj.hatali")}</p>
        ) : null}

        {eylemlerGorunur ? (
          <Buton
            tur="hayalet"
            boyut="kucuk"
            onClick={onYenidenUret}
            aria-label={t("sohbet.mesaj.yeniden.etiket")}
          >
            <RefreshCw aria-hidden className="size-3.5" />
            {kullaniciMi ? t("sohbet.mesaj.yeniden.kullanici") : t("sohbet.mesaj.yeniden")}
          </Buton>
        ) : null}
      </div>
    </article>
  );
});
