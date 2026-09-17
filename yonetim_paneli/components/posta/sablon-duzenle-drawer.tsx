"use client";

import { useState } from "react";

import { useDil } from "@/lib/dil";
import {
  SABLON_DILI_ANAHTARI,
  SABLON_KODU_ANAHTARI,
  degiskenleriBul,
  sablonHatasi,
  sablonKaydet,
  type PostaSablonu,
} from "@/lib/posta-sablonlari";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";

/** `PUT /posta-sablonlari` — konu ve gövdeyi organizasyon için kaydeder. */
export function SablonDuzenleDrawer({
  sablon,
  onKapat,
  onKaydedildi,
}: {
  sablon: PostaSablonu;
  onKapat: () => void;
  onKaydedildi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [konu, setKonu] = useState(sablon.konu);
  const [govdeMetin, setGovdeMetin] = useState(sablon.govde_metin);
  const [govdeHtml, setGovdeHtml] = useState(sablon.govde_html);
  const [konuHata, setKonuHata] = useState<string | null>(null);
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);

  const degiskenler = degiskenleriBul(konu, govdeMetin, govdeHtml);

  const kaydet = async () => {
    if (!konu.trim()) {
      setKonuHata(t("posta.duzenle.konu.zorunlu"));
      return;
    }
    setKonuHata(null);

    const degistiMi =
      konu !== sablon.konu ||
      govdeMetin !== sablon.govde_metin ||
      govdeHtml !== sablon.govde_html;
    if (!degistiMi) {
      showToast(t("posta.duzenle.degisiklik_yok"), "info");
      return;
    }

    setKaydediliyor(true);
    setSunucuHatasi(null);
    try {
      await sablonKaydet({
        kod: sablon.kod,
        dil: sablon.dil,
        konu: konu.trim(),
        govde_metin: govdeMetin,
        govde_html: govdeHtml,
      });
      showToast(t("posta.duzenle.basarili"), "success");
      onKaydedildi();
      onKapat();
    } catch (sebep) {
      setSunucuHatasi(sablonHatasi(sebep));
    } finally {
      setKaydediliyor(false);
    }
  };

  return (
    <Drawer
      open
      onClose={() => {
        if (!kaydediliyor) onKapat();
      }}
      title={t("posta.duzenle.baslik", {
        ad: t(SABLON_KODU_ANAHTARI[sablon.kod]),
        dil: t(SABLON_DILI_ANAHTARI[sablon.dil]),
      })}
      description={t("posta.duzenle.aciklama")}
      className="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={kaydediliyor}>
            {t("genel.vazgec")}
          </Button>
          <Button loading={kaydediliyor} onClick={() => void kaydet()}>
            {t("posta.duzenle.kaydet")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("posta.duzenle.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Alert tone={sablon.ozel ? "info" : "warning"}>
          {t(sablon.ozel ? "posta.ozel.ipucu" : "posta.varsayilan.ipucu")}
        </Alert>

        <Field label={t("posta.duzenle.konu")} error={konuHata} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              value={konu}
              onChange={(olay) => setKonu(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("posta.duzenle.govde_metin")} hint={t("posta.degisken.ipucu")}>
          {({ id, ...erisim }) => (
            <Textarea
              id={id}
              {...erisim}
              rows={10}
              value={govdeMetin}
              onChange={(olay) => setGovdeMetin(olay.target.value)}
            />
          )}
        </Field>

        <Field
          label={t("posta.duzenle.govde_html")}
          hint={t("posta.duzenle.govde_html.ipucu")}
        >
          {({ id, ...erisim }) => (
            <Textarea
              id={id}
              {...erisim}
              rows={10}
              className="font-mono text-xs"
              value={govdeHtml}
              onChange={(olay) => setGovdeHtml(olay.target.value)}
            />
          )}
        </Field>

        {degiskenler.length > 0 ? (
          <div className="flex flex-col gap-2">
            <p className="text-xs tracking-wide text-neutral-500 uppercase">
              {t("posta.onizle.degiskenler")}
            </p>
            <ul className="flex flex-wrap gap-2">
              {degiskenler.map((degisken) => (
                <li key={degisken}>
                  <Badge tone="neutral">{`{{${degisken}}}`}</Badge>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </Drawer>
  );
}
