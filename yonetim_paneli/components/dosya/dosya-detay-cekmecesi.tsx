"use client";

import { ApiHatasi } from "@/lib/api";
import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { boyutBicimle, dosyaDetayiGetir, type DosyaDetayi, type DosyaOzeti } from "@/lib/dosyalar";
import { useUzakVeri } from "@/lib/kancalar";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Alert } from "@/components/ui/alert";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";

function BilgiSatiri({ etiket, deger }: { etiket: string; deger: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs tracking-wide text-neutral-500 uppercase">{etiket}</dt>
      <dd className="text-sm break-words text-neutral-900">{deger}</dd>
    </div>
  );
}

export type DosyaDetayCekmecesiProps = {
  dosya: DosyaOzeti;
  onKapat: () => void;
};

/**
 * Dosya metası ve maskelenmiş çıkarılmış metni.
 * Başka organizasyonun kaydı `404` döner; bu "kayıt yok" olarak gösterilir.
 */
export function DosyaDetayCekmecesi({ dosya, onKapat }: DosyaDetayCekmecesiProps) {
  const { t } = useDil();

  const detay = useUzakVeri<DosyaDetayi | null>(async () => {
    try {
      return await dosyaDetayiGetir(dosya.id);
    } catch (sebep) {
      if (sebep instanceof ApiHatasi && sebep.durum === 404) return null;
      throw sebep;
    }
  }, [dosya.id]);

  return (
    <Drawer open onClose={onKapat} title={t("dosya.detay.baslik")} description={dosya.ad}>
      <VeriDurumu yukleniyor={detay.yukleniyor} hata={detay.hata} yenile={detay.yenile}>
        {detay.veri === null ? (
          <EmptyState title={t("dosya.detay.bulunamadi")} />
        ) : detay.veri ? (
          <div className="flex flex-col gap-4">
            <Alert tone="info" title={t("dosya.detay.maskeleme.baslik")}>
              {t("dosya.detay.maskeleme.govde")}
            </Alert>

            <dl className="grid grid-cols-2 gap-4">
              <BilgiSatiri etiket={t("dosya.detay.ad")} deger={detay.veri.ad} />
              <BilgiSatiri etiket={t("dosya.detay.mime")} deger={detay.veri.mime} />
              <BilgiSatiri
                etiket={t("dosya.detay.boyut")}
                deger={boyutBicimle(detay.veri.boyut)}
              />
              <BilgiSatiri
                etiket={t("dosya.detay.metin_uzunluk")}
                deger={t("dosya.metin.uzunluk", {
                  sayi: sayiBicimle(detay.veri.metin_uzunluk),
                })}
              />
              <BilgiSatiri
                etiket={t("dosya.detay.yukleyen")}
                deger={detay.veri.kullanici_id === null ? "—" : String(detay.veri.kullanici_id)}
              />
              <BilgiSatiri
                etiket={t("dosya.detay.olusturulma")}
                deger={tarihSaatBicimle(detay.veri.olusturulma)}
              />
            </dl>

            <div className="flex flex-col gap-0.5">
              <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                {t("dosya.detay.sha256")}
              </dt>
              <dd className="font-mono text-xs break-all text-neutral-700">
                {detay.veri.sha256}
              </dd>
            </div>

            <section className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold text-neutral-900">
                {t("dosya.detay.metin")}
              </h3>
              {detay.veri.metin.trim() ? (
                <pre className="max-h-96 overflow-auto rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-xs break-words whitespace-pre-wrap text-neutral-800">
                  {detay.veri.metin}
                </pre>
              ) : (
                <p className="text-sm text-neutral-500">{t("dosya.detay.metin.yok")}</p>
              )}
            </section>
          </div>
        ) : null}
      </VeriDurumu>
    </Drawer>
  );
}
