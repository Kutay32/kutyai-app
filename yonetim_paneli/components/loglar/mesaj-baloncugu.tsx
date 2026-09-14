"use client";

import { cn } from "@/lib/cn";
import { gecikmeBicimle, sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import type { LogMesaji } from "@/lib/loglar";
import { Alert } from "@/components/ui/alert";
import { Badge, type BadgeTone } from "@/components/ui/badge";

const ROL_TONU: Record<LogMesaji["rol"], BadgeTone> = {
  kullanici: "info",
  asistan: "neutral",
  sistem: "warning",
  arac: "success",
};

const BALON_GORUNUMU: Record<LogMesaji["rol"], string> = {
  kullanici: "border-neutral-200 bg-white",
  asistan: "border-neutral-200 bg-neutral-50",
  sistem: "border-dashed border-neutral-300 bg-neutral-100",
  arac: "border-neutral-200 bg-white",
};

/** Tek kayıt mesajını, kayıtta saklandığı (maskelenmiş) hâliyle gösterir. */
export function MesajBaloncugu({ mesaj, etiket }: { mesaj: LogMesaji; etiket: string }) {
  const { t } = useDil();
  const kullaniciMi = mesaj.rol === "kullanici";

  return (
    <div className={cn("flex", kullaniciMi ? "md:justify-end" : "md:justify-start")}>
      <article
        className={cn(
          "flex w-full max-w-2xl flex-col gap-2 rounded-lg border p-4",
          BALON_GORUNUMU[mesaj.rol],
        )}
      >
        <header className="flex flex-wrap items-center gap-2 text-xs text-neutral-500">
          <Badge tone={ROL_TONU[mesaj.rol]}>
            {etiket}
          </Badge>
          <span className="text-neutral-800">#{mesaj.id}</span>
          {mesaj.model ? <span>{mesaj.model}</span> : null}
          <span>{t("kayit.mesaj.token", { sayi: sayiBicimle(mesaj.token_sayisi) })}</span>
          {mesaj.gecikme_ms > 0 ? <span>{gecikmeBicimle(mesaj.gecikme_ms)}</span> : null}
          <time dateTime={mesaj.olusturulma} className="ml-auto">
            {tarihSaatBicimle(mesaj.olusturulma)}
          </time>
        </header>

        <p className="text-sm break-words whitespace-pre-wrap text-neutral-800">
          {mesaj.icerik || t("kayit.mesaj.bos_icerik")}
        </p>

        {mesaj.hata ? (
          <Alert tone="danger" title={t("kayit.mesaj.saglayici_hatasi")}>
            {mesaj.hata}
          </Alert>
        ) : null}
      </article>
    </div>
  );
}
