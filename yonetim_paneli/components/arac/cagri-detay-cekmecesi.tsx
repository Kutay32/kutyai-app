"use client";

import { gecikmeBicimle, tarihSaatBicimle } from "@/lib/bicim";
import type { AracCagrisi } from "@/lib/araclar";
import { useDil } from "@/lib/dil";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Drawer } from "@/components/ui/drawer";

function BilgiSatiri({ etiket, deger }: { etiket: string; deger: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs tracking-wide text-neutral-500 uppercase">{etiket}</dt>
      <dd className="text-sm break-words text-neutral-900">{deger}</dd>
    </div>
  );
}

function JsonBlok({ baslik, veri }: { baslik: string; veri: unknown }) {
  return (
    <section className="flex flex-col gap-1">
      <h3 className="text-xs font-medium tracking-wide text-neutral-500 uppercase">{baslik}</h3>
      <pre className="max-h-64 overflow-auto rounded-md border border-neutral-200 bg-neutral-50 p-2 font-mono text-xs break-words whitespace-pre-wrap text-neutral-800">
        {JSON.stringify(veri, null, 2)}
      </pre>
    </section>
  );
}

export type CagriDetayCekmecesiProps = {
  kayit: AracCagrisi;
  onKapat: () => void;
};

/** Tek araç çağrısının argümanları, sonucu ve varsa hata metni. */
export function CagriDetayCekmecesi({ kayit, onKapat }: CagriDetayCekmecesiProps) {
  const { t } = useDil();

  return (
    <Drawer open onClose={onKapat} title={t("arac.cagri.detay.baslik")} description={kayit.ad}>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={kayit.durum === "basarili" ? "success" : "danger"}>
            {kayit.durum === "basarili"
              ? t("arac.cagri.durum.basarili")
              : t("arac.cagri.durum.hata")}
          </Badge>
          <span className="text-xs text-neutral-500">
            {t("arac.dene.gecikme")}: {gecikmeBicimle(kayit.gecikme_ms)}
          </span>
        </div>

        <dl className="grid grid-cols-2 gap-4">
          <BilgiSatiri etiket={t("arac.cagri.tablo.arac")} deger={kayit.ad} />
          <BilgiSatiri
            etiket={t("arac.cagri.tablo.olusturulma")}
            deger={tarihSaatBicimle(kayit.olusturulma)}
          />
          <BilgiSatiri
            etiket={t("arac.cagri.konusma")}
            deger={kayit.konusma_id === null ? t("arac.cagri.panel") : `#${kayit.konusma_id}`}
          />
          <BilgiSatiri
            etiket={t("arac.cagri.arac_id")}
            deger={kayit.arac_id === null ? "—" : `#${kayit.arac_id}`}
          />
        </dl>

        {kayit.hata ? (
          <Alert tone="danger" title={t("arac.cagri.hata")}>
            {kayit.hata}
          </Alert>
        ) : null}

        <JsonBlok baslik={t("arac.cagri.argumanlar")} veri={kayit.argumanlar} />
        <JsonBlok baslik={t("arac.cagri.sonuc")} veri={kayit.sonuc} />
      </div>
    </Drawer>
  );
}
