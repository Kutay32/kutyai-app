"use client";

import { ApiHatasi } from "@/lib/api";
import { sayiBicimle, tarihSaatBicimle } from "@/lib/bicim";
import {
  KAYNAK_ANAHTARI,
  belgeDetayiGetir,
  type BelgeDetayi,
  type BelgeOzeti,
} from "@/lib/bilgi-tabani";
import { useDil } from "@/lib/dil";
import { useUzakVeri } from "@/lib/kancalar";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Badge } from "@/components/ui/badge";
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

export type BelgeDetayCekmecesiProps = {
  belge: BelgeOzeti;
  onKapat: () => void;
};

/**
 * Belgenin parçaları (gömülen birimler) ve metası.
 * Başka organizasyonun kaydı `404` döner; bu "kayıt yok" olarak gösterilir.
 */
export function BelgeDetayCekmecesi({ belge, onKapat }: BelgeDetayCekmecesiProps) {
  const { t } = useDil();

  const detay = useUzakVeri<BelgeDetayi | null>(async () => {
    try {
      return await belgeDetayiGetir(belge.id);
    } catch (sebep) {
      if (sebep instanceof ApiHatasi && sebep.durum === 404) return null;
      throw sebep;
    }
  }, [belge.id]);

  return (
    <Drawer open onClose={onKapat} title={t("bilgi.detay.baslik")} description={belge.ad}>
      <VeriDurumu yukleniyor={detay.yukleniyor} hata={detay.hata} yenile={detay.yenile}>
        {detay.veri === null ? (
          <EmptyState title={t("bilgi.detay.bulunamadi")} />
        ) : detay.veri ? (
          <div className="flex flex-col gap-4">
            <dl className="grid grid-cols-2 gap-4">
              <BilgiSatiri etiket={t("bilgi.detay.ad")} deger={detay.veri.ad} />
              <BilgiSatiri
                etiket={t("bilgi.detay.kaynak")}
                deger={t(KAYNAK_ANAHTARI[detay.veri.kaynak])}
              />
              <BilgiSatiri
                etiket={t("bilgi.detay.parca_sayisi")}
                deger={sayiBicimle(detay.veri.parca_sayisi)}
              />
              <BilgiSatiri
                etiket={t("bilgi.detay.olusturulma")}
                deger={tarihSaatBicimle(detay.veri.olusturulma)}
              />
              {detay.veri.dosya_id !== null ? (
                <BilgiSatiri
                  etiket={t("bilgi.detay.dosya")}
                  deger={String(detay.veri.dosya_id)}
                />
              ) : null}
            </dl>

            {detay.veri.parcalar.length === 0 ? (
              <p className="text-sm text-neutral-500">{t("bilgi.detay.parca.yok")}</p>
            ) : (
              <ol className="flex flex-col gap-3">
                {detay.veri.parcalar.map((parca) => (
                  <li
                    key={parca.sira}
                    className="flex flex-col gap-2 rounded-lg border border-neutral-200 p-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-medium tracking-wide text-neutral-500 uppercase">
                        {t("bilgi.detay.parca", { sira: parca.sira + 1 })}
                      </span>
                      <Badge tone="neutral">
                        {t("bilgi.detay.token", { sayi: sayiBicimle(parca.token_sayisi) })}
                      </Badge>
                    </div>
                    <p className="text-sm break-words whitespace-pre-wrap text-neutral-700">
                      {parca.icerik}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        ) : null}
      </VeriDurumu>
    </Drawer>
  );
}
