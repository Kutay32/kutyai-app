"use client";

import { useState } from "react";

import { hataMesaji } from "@/lib/api";
import { yonlendirmeGuncelle, type BdmKaydi } from "@/lib/bdm";
import { useDil } from "@/lib/dil";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

export type SekmeYonlendirmeProps = {
  bdm: BdmKaydi;
  /** Güncellenen kaydı üst sayfaya bildirir. */
  onGuncellendi: (bdm: BdmKaydi) => void;
};

/** Yönlendirme sekmesi: takma ad ve öncelik (PATCH /bdm/yonetim/{id}/yol). */
export function SekmeYonlendirme({ bdm, onGuncellendi }: SekmeYonlendirmeProps) {
  const { showToast } = useToast();
  const { t } = useDil();
  const [takmaAd, setTakmaAd] = useState(bdm.konteyner?.yol?.takma_ad ?? "");
  const [oncelik, setOncelik] = useState(
    bdm.konteyner?.yol?.oncelik === undefined ? "" : String(bdm.konteyner.yol.oncelik),
  );
  const [hatalar, setHatalar] = useState<{ takma_ad?: string; oncelik?: string }>({});
  const [genelHata, setGenelHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();

    const bulunan: { takma_ad?: string; oncelik?: string } = {};
    const ad = takmaAd.trim();
    if (ad.length > 80) bulunan.takma_ad = t("bdm.yonlendirme.hata.takma_ad");
    const oncelikSayi = oncelik.trim() === "" ? null : Number(oncelik);
    if (oncelikSayi !== null && (!Number.isInteger(oncelikSayi) || oncelikSayi < 0 || oncelikSayi > 1000)) {
      bulunan.oncelik = t("bdm.yonlendirme.hata.oncelik");
    }
    setHatalar(bulunan);
    if (Object.keys(bulunan).length > 0) return;

    setGonderiliyor(true);
    setGenelHata(null);
    try {
      const kayit = await yonlendirmeGuncelle(bdm.id, {
        ...(ad ? { takma_ad: ad } : {}),
        ...(oncelikSayi === null ? {} : { oncelik: oncelikSayi }),
      });
      showToast(t("bdm.bildirim.yonlendirme_kaydedildi"), "success");
      onGuncellendi(kayit);
    } catch (sebep) {
      setGenelHata(hataMesaji(sebep));
    } finally {
      setGonderiliyor(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("bdm.yonlendirme.baslik")}</CardTitle>
        <CardDescription>{t("bdm.yonlendirme.aciklama")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={kaydet} className="flex flex-col gap-4" noValidate>
          {genelHata ? <Alert tone="danger">{genelHata}</Alert> : null}

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field
              label={t("bdm.alan.takma_ad")}
              hint={t("bdm.yonlendirme.takma_ad.ipucu")}
              error={hatalar.takma_ad}
            >
              {(props) => (
                <Input
                  {...props}
                  invalid={props.invalid}
                  value={takmaAd}
                  onChange={(olay) => {
                    setTakmaAd(olay.target.value);
                    setHatalar((onceki) => ({ ...onceki, takma_ad: undefined }));
                  }}
                  placeholder="kutyai-hizli"
                />
              )}
            </Field>

            <Field
              label={t("bdm.alan.oncelik")}
              hint={t("bdm.yonlendirme.oncelik.ipucu")}
              error={hatalar.oncelik}
            >
              {(props) => (
                <Input
                  {...props}
                  invalid={props.invalid}
                  type="number"
                  value={oncelik}
                  onChange={(olay) => {
                    setOncelik(olay.target.value);
                    setHatalar((onceki) => ({ ...onceki, oncelik: undefined }));
                  }}
                  placeholder="100"
                />
              )}
            </Field>
          </div>

          <div>
            <Button type="submit" loading={gonderiliyor}>
              {t("bdm.kaydet")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
