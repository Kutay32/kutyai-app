"use client";

import { useEffect, useState } from "react";

import { RefreshCw, Save } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { zorunluHatasi } from "@/lib/dogrulama";
import {
  VARSAYILAN_SAKLAMA_GUNU,
  ayarlariGetir,
  ayarlariGuncelle,
  type AyarGuncellemesi,
  type Ayarlar,
} from "@/lib/ayarlar";
import { useUzakVeri } from "@/lib/kancalar";
import { aktifDil, ceviri } from "@/lib/sozluk";
import { VeriDurumu } from "@/components/loglar/veri-durumu";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { LogTemizlemeKarti } from "./log-temizleme";

const EN_BUYUK_SAKLAMA_GUNU = 3650;

type TlsSecimi = "degistirme" | "acik" | "kapali";

type AyarFormu = {
  marka_adi: string;
  kayit_acik: boolean;
  maskeleme_aktif: boolean;
  saklama_gun: string;
  bakim_modu: boolean;
  smtp_host: string;
  smtp_port: string;
  smtp_kullanici: string;
  smtp_sifre: string;
  smtp_gonderen: string;
  smtp_tls: TlsSecimi;
};

/** Sunucudan gelen ayarları düzenlenebilir form durumuna çevirir. */
function formdan(ayarlar: Ayarlar): AyarFormu {
  return {
    marka_adi: ayarlar.marka_adi,
    kayit_acik: ayarlar.kayit_acik,
    maskeleme_aktif: ayarlar.maskeleme_aktif,
    saklama_gun: String(ayarlar.saklama_gun),
    bakim_modu: ayarlar.bakim_modu,
    smtp_host: ayarlar.smtp_host,
    // Sunucu bu alanları geri döndürmez; yalnızca değiştirileceği zaman doldurulur.
    smtp_port: "",
    smtp_kullanici: "",
    smtp_sifre: "",
    smtp_gonderen: ayarlar.smtp_gonderen,
    smtp_tls: "degistirme",
  };
}

type FormHatalari = { marka_adi?: string; saklama_gun?: string; smtp_port?: string };

/**
 * Formu doğrular ve yalnızca gönderilecek alanları içeren gövdeyi üretir.
 * Modül düzeyinde olduğu için doğrulama mesajları `ceviri` ile aktif dilde üretilir.
 */
function govdeUret(form: AyarFormu): { govde: AyarGuncellemesi; hatalar: FormHatalari } {
  const hatalar: FormHatalari = {};
  const markaHatasi = zorunluHatasi(form.marka_adi, ceviri("genel.marka_adi", aktifDil()));
  if (markaHatasi) hatalar.marka_adi = markaHatasi;

  const saklama = Number(form.saklama_gun);
  if (!Number.isInteger(saklama) || saklama < 1 || saklama > EN_BUYUK_SAKLAMA_GUNU) {
    hatalar.saklama_gun = ceviri("ayarlar.saklama.hata", aktifDil(), {
      azami: EN_BUYUK_SAKLAMA_GUNU,
    });
  }

  const port = form.smtp_port ? Number(form.smtp_port) : null;
  if (port !== null && (!Number.isInteger(port) || port < 1 || port > 65535)) {
    hatalar.smtp_port = ceviri("ayarlar.smtp.port.hata", aktifDil());
  }

  if (Object.keys(hatalar).length > 0) return { govde: {}, hatalar };

  const govde: AyarGuncellemesi = {
    marka_adi: form.marka_adi.trim(),
    kayit_acik: form.kayit_acik,
    maskeleme_aktif: form.maskeleme_aktif,
    saklama_gun: saklama,
    bakim_modu: form.bakim_modu,
    // Boş dize SMTP'yi kapatır; alan her kayıtta gönderilir.
    smtp_host: form.smtp_host.trim(),
    smtp_gonderen: form.smtp_gonderen.trim(),
  };
  if (port !== null) govde.smtp_port = port;
  if (form.smtp_kullanici.trim()) govde.smtp_kullanici = form.smtp_kullanici.trim();
  if (form.smtp_sifre) govde.smtp_sifre = form.smtp_sifre;
  if (form.smtp_tls !== "degistirme") govde.smtp_tls = form.smtp_tls === "acik";

  return { govde, hatalar };
}

/** Bakım modu uyarısı: uç yolları ve durum kodu cümle içinde vurgulu kalır. */
function BakimModuUyarisi() {
  const { t } = useDil();
  // Şablon `{uc1}`, `{uc2}` ve `{kodu}` yer tutucularından parçalanır.
  const [bas, uc1Sonrasi] = t("ayarlar.bakim.uyari.metin").split("{uc1}");
  const [orta, uc2Sonrasi] = uc1Sonrasi.split("{uc2}");
  const [ucOncesi, son] = uc2Sonrasi.split("{kodu}");

  return (
    <Alert tone="warning" title={t("ayarlar.bakim.uyari.baslik")}>
      {bas}
      <code>/sohbet</code>
      {orta}
      <code>/sohbet/akis</code>
      {ucOncesi}
      <code>503</code>
      {son}
    </Alert>
  );
}

export default function AyarlarSayfasi() {
  const { showToast } = useToast();
  const { t } = useDil();
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<Ayarlar>(ayarlariGetir, []);
  const [form, setForm] = useState<AyarFormu | null>(null);
  const [hatalar, setHatalar] = useState<FormHatalari>({});
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [kaydetmeHatasi, setKaydetmeHatasi] = useState<string | null>(null);

  // Kayıt politikası ipucundaki uç yolu cümle içinde vurgulu kalır.
  const [kayitOnce, kayitSonrasi] = t("ayarlar.kayit.ipucu").split("{kod}");

  useEffect(() => {
    if (veri) {
      setForm(formdan(veri));
      setHatalar({});
    }
  }, [veri]);

  const guncelle = <Alan extends keyof AyarFormu>(alan: Alan, deger: AyarFormu[Alan]) => {
    setForm((onceki) => (onceki ? { ...onceki, [alan]: deger } : onceki));
  };

  const kaydet = async () => {
    if (!form) return;
    const { govde, hatalar: bulunanlar } = govdeUret(form);
    setHatalar(bulunanlar);
    if (Object.keys(bulunanlar).length > 0) return;

    setKaydediliyor(true);
    setKaydetmeHatasi(null);
    try {
      await ayarlariGuncelle(govde);
      showToast(t("ayarlar.kaydedildi"), "success");
      yenile();
    } catch (sebep) {
      setKaydetmeHatasi(hataMesaji(sebep));
    } finally {
      setKaydediliyor(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">
          {t("menu.ayarlar")}
        </h1>
        <p className="text-sm text-neutral-500">{t("ayarlar.aciklama")}</p>
      </header>

      <VeriDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {form && veri ? (
          <div className="flex flex-col gap-6">
            {kaydetmeHatasi ? (
              <Alert tone="danger" title={t("ayarlar.kaydedilemedi")}>
                {kaydetmeHatasi}
              </Alert>
            ) : null}

            {form.bakim_modu ? <BakimModuUyarisi /> : null}

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>{t("ayarlar.genel.baslik")}</CardTitle>
                <CardDescription>{t("ayarlar.genel.aciklama")}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Field label={t("genel.marka_adi")} error={hatalar.marka_adi} required>
                  {({ id, invalid, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      invalid={invalid}
                      value={form.marka_adi}
                      onChange={(olay) => guncelle("marka_adi", olay.target.value)}
                    />
                  )}
                </Field>

                <Field
                  label={t("ayarlar.saklama")}
                  error={hatalar.saklama_gun}
                  hint={t("ayarlar.saklama.ipucu", { gun: VARSAYILAN_SAKLAMA_GUNU })}
                  required
                >
                  {({ id, invalid, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      invalid={invalid}
                      type="number"
                      min={1}
                      max={EN_BUYUK_SAKLAMA_GUNU}
                      value={form.saklama_gun}
                      onChange={(olay) => guncelle("saklama_gun", olay.target.value)}
                    />
                  )}
                </Field>

                <div className="flex flex-col gap-3">
                  <Label>{t("ayarlar.kayit.baslik")}</Label>
                  <Switch
                    checked={form.kayit_acik}
                    onChange={(deger) => guncelle("kayit_acik", deger)}
                    label={t("ayarlar.kayit.anahtar")}
                  />
                  <p className="text-xs text-neutral-500">
                    {kayitOnce}
                    <code>/kimlik/kayit</code>
                    {kayitSonrasi}
                  </p>
                </div>

                <div className="flex flex-col gap-3">
                  <Label>{t("ayarlar.maskeleme.baslik")}</Label>
                  <Switch
                    checked={form.maskeleme_aktif}
                    onChange={(deger) => guncelle("maskeleme_aktif", deger)}
                    label={t("ayarlar.maskeleme.anahtar")}
                  />
                  <p className="text-xs text-neutral-500">{t("ayarlar.maskeleme.ipucu")}</p>
                </div>

                <div className="flex flex-col gap-3 md:col-span-2">
                  <Label>{t("ayarlar.bakim.baslik")}</Label>
                  <Switch
                    checked={form.bakim_modu}
                    onChange={(deger) => guncelle("bakim_modu", deger)}
                    label={t("ayarlar.bakim.anahtar")}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>{t("ayarlar.smtp.baslik")}</CardTitle>
                  <Badge tone={veri.smtp_tanimli ? "success" : "neutral"}>
                    {veri.smtp_tanimli ? t("ayarlar.smtp.tanimli") : t("ayarlar.smtp.tanimsiz")}
                  </Badge>
                </div>
                <CardDescription>{t("ayarlar.smtp.aciklama")}</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Field label={t("ayarlar.smtp.sunucu")} hint={t("ayarlar.smtp.sunucu.ipucu")}>
                  {({ id, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      value={form.smtp_host}
                      onChange={(olay) => guncelle("smtp_host", olay.target.value)}
                    />
                  )}
                </Field>

                <Field
                  label={t("ayarlar.smtp.port")}
                  error={hatalar.smtp_port}
                  hint={t("ayarlar.yalniz_yazilir.ipucu")}
                >
                  {({ id, invalid, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      invalid={invalid}
                      type="number"
                      min={1}
                      max={65535}
                      placeholder="587"
                      value={form.smtp_port}
                      onChange={(olay) => guncelle("smtp_port", olay.target.value)}
                    />
                  )}
                </Field>

                <Field
                  label={t("ayarlar.smtp.kullanici")}
                  hint={t("ayarlar.yalniz_yazilir.ipucu")}
                >
                  {({ id, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      autoComplete="off"
                      value={form.smtp_kullanici}
                      onChange={(olay) => guncelle("smtp_kullanici", olay.target.value)}
                    />
                  )}
                </Field>

                <Field label={t("genel.parola")} hint={t("ayarlar.smtp.sifre.ipucu")}>
                  {({ id, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      type="password"
                      autoComplete="new-password"
                      value={form.smtp_sifre}
                      onChange={(olay) => guncelle("smtp_sifre", olay.target.value)}
                    />
                  )}
                </Field>

                <Field label={t("ayarlar.smtp.gonderen")}>
                  {({ id, ...erisim }) => (
                    <Input
                      id={id}
                      {...erisim}
                      type="email"
                      value={form.smtp_gonderen}
                      onChange={(olay) => guncelle("smtp_gonderen", olay.target.value)}
                    />
                  )}
                </Field>

                <Field
                  label={t("ayarlar.smtp.tls")}
                  hint={t("ayarlar.yalniz_yazilir.ipucu")}
                >
                  {({ id, ...erisim }) => (
                    <Select
                      id={id}
                      {...erisim}
                      value={form.smtp_tls}
                      onChange={(olay) => guncelle("smtp_tls", olay.target.value as TlsSecimi)}
                    >
                      <option value="degistirme">{t("ayarlar.tls.degistirme")}</option>
                      <option value="acik">{t("ayarlar.tls.acik")}</option>
                      <option value="kapali">{t("ayarlar.tls.kapali")}</option>
                    </Select>
                  )}
                </Field>
              </CardContent>
            </Card>

            <div className="flex items-center gap-2">
              <Button loading={kaydediliyor} onClick={() => void kaydet()}>
                <Save aria-hidden className="size-4" />
                {t("ayarlar.kaydet")}
              </Button>
              <Button
                variant="ghost"
                onClick={yenile}
                disabled={kaydediliyor}
              >
                <RefreshCw aria-hidden className="size-4" />
                {t("ayarlar.sunucudan_yenile")}
              </Button>
            </div>

            <LogTemizlemeKarti saklamaGunu={veri.saklama_gun} onTemizlendi={yenile} />
          </div>
        ) : null}
      </VeriDurumu>
    </div>
  );
}
