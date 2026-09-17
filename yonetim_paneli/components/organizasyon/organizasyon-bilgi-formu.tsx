"use client";

import { useState } from "react";

import { useDil } from "@/lib/dil";
import { ORGANIZASYON_DURUMU_ANAHTARI } from "@/lib/etiketler";
import {
  ORGANIZASYON_DURUMLARI,
  organizasyonGuncelle,
  organizasyonHatasi,
  organizasyonYonetebilirMi,
} from "@/lib/organizasyonlar";
import type { Organizasyon, OrganizasyonDurumu } from "@/lib/tipler";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

export type OrganizasyonBilgiFormuProps = {
  organizasyon: Organizasyon;
  onKaydedildi: () => void;
};

/**
 * `PATCH /organizasyonlar/{id}` — ad ve durum. Çağrı yerinde `key={organizasyon.id}`
 * verilerek seçim değişiminde form durumu sıfırlanır.
 */
export function OrganizasyonBilgiFormu({
  organizasyon,
  onKaydedildi,
}: OrganizasyonBilgiFormuProps) {
  const { t } = useDil();
  const { showToast } = useToast();
  const yonetebilir = organizasyonYonetebilirMi(organizasyon.rol);

  const [ad, setAd] = useState(organizasyon.ad);
  const [durum, setDurum] = useState<OrganizasyonDurumu>(organizasyon.durum);
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const kaydet = async () => {
    const degisiklikler: { ad?: string; durum?: OrganizasyonDurumu } = {};
    if (ad.trim() !== organizasyon.ad) degisiklikler.ad = ad.trim();
    if (durum !== organizasyon.durum) degisiklikler.durum = durum;

    if (Object.keys(degisiklikler).length === 0) {
      showToast(t("organizasyon.bilgi.degisiklik_yok"), "info");
      return;
    }

    setKaydediliyor(true);
    setHata(null);
    try {
      await organizasyonGuncelle(organizasyon.id, degisiklikler);
      showToast(t("organizasyon.bilgi.basarili"), "success");
      onKaydedildi();
    } catch (sebep) {
      setHata(organizasyonHatasi(sebep));
    } finally {
      setKaydediliyor(false);
    }
  };

  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle>{t("organizasyon.bilgi.baslik")}</CardTitle>
        <CardDescription>{t("organizasyon.bilgi.aciklama")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {hata ? (
          <Alert tone="danger" title={t("organizasyon.bilgi.hata.baslik")}>
            {hata}
          </Alert>
        ) : null}

        <Field label={t("organizasyon.bilgi.ad")} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              value={ad}
              disabled={!yonetebilir || kaydediliyor}
              onChange={(olay) => setAd(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("organizasyon.bilgi.durum")}>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={durum}
              disabled={!yonetebilir || kaydediliyor}
              onChange={(olay) => setDurum(olay.target.value as OrganizasyonDurumu)}
            >
              {ORGANIZASYON_DURUMLARI.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {t(ORGANIZASYON_DURUMU_ANAHTARI[secenek])}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-neutral-500">
            {t("organizasyon.tablo.slug")}: <span className="font-mono">{organizasyon.slug}</span>
          </p>
          <Button
            loading={kaydediliyor}
            disabled={!yonetebilir}
            onClick={() => void kaydet()}
          >
            {t("organizasyon.bilgi.kaydet")}
          </Button>
        </div>

        {!yonetebilir ? <Alert tone="info">{t("organizasyon.yetki.ipucu")}</Alert> : null}
      </CardContent>
    </Card>
  );
}
