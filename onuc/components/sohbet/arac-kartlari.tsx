"use client";

import { CheckCircle2, Loader2, Wrench, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import { ARAC_DURUM_ANAHTARLARI, type AracKarti } from "@/lib/sohbet";

export type AracKartlariOzellikleri = {
  kartlar: AracKarti[];
};

const DURUM_SINIFLARI: Record<AracKarti["durum"], string> = {
  calisiyor: "border-neutral-200 text-neutral-500",
  basarili: "border-green-200 text-green-800",
  hata: "border-rose-200 text-rose-600",
};

function DurumSimgesi({ durum }: { durum: AracKarti["durum"] }) {
  const sinif = "size-3.5 shrink-0";
  if (durum === "calisiyor") return <Loader2 aria-hidden className={cn(sinif, "animate-spin")} />;
  if (durum === "basarili") return <CheckCircle2 aria-hidden className={sinif} />;
  return <XCircle aria-hidden className={sinif} />;
}

/**
 * Araç çağrısı kartları: canlı SSE olayları (`arac_cagrisi`/`arac_sonucu`) ile
 * yanıt özetinin (`arac_cagrilari`) birleşimi.
 */
export function AracKartlari({ kartlar }: AracKartlariOzellikleri) {
  const { t } = useDil();
  if (kartlar.length === 0) return null;

  return (
    <section aria-label={t("sohbet.arac.baslik")} className="flex flex-col gap-2">
      <h4 className="flex items-center gap-1.5 text-[13px] font-medium text-neutral-900">
        <Wrench aria-hidden className="size-3.5" />
        {t("sohbet.arac.baslik")}
      </h4>
      <ul className="flex flex-col gap-2">
        {kartlar.map((kart, sira) => (
          <li
            key={`${kart.ad}-${sira}`}
            className={cn("rounded-lg border bg-white p-2.5 text-[13px]", DURUM_SINIFLARI[kart.durum])}
          >
            <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
              <span className="min-w-0 truncate font-medium text-neutral-900">{kart.ad}</span>
              <span className="inline-flex shrink-0 items-center gap-1">
                <DurumSimgesi durum={kart.durum} />
                {t(ARAC_DURUM_ANAHTARLARI[kart.durum])}
              </span>
            </div>
            {kart.argumanlar ? (
              <div className="mt-2">
                <p className="text-[11px] text-neutral-500">{t("sohbet.arac.argumanlar")}</p>
                <pre className="mt-1 overflow-x-auto rounded-md bg-neutral-50 p-2 font-mono text-[11px] break-words whitespace-pre-wrap text-neutral-600">
                  {JSON.stringify(kart.argumanlar, null, 2)}
                </pre>
              </div>
            ) : null}
            {kart.ozet ? (
              <div className="mt-2">
                <p className="text-[11px] text-neutral-500">{t("sohbet.arac.ozet")}</p>
                <p className="mt-0.5 break-words text-neutral-600">{kart.ozet}</p>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
