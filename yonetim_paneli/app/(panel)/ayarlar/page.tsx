"use client";

import { useEffect, useState } from "react";

import { RefreshCw, Save } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { zorunluHatasi } from "@/lib/dogrulama";
import {
  VARSAYILAN_SAKLAMA_GUNU,
  ayarlariGetir,
  ayarlariGuncelle,
  type AyarGuncellemesi,
  type Ayarlar,
} from "@/lib/ayarlar";
import { useUzakVeri } from "@/lib/kancalar";
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

/** Formu doğrular ve yalnızca gönderilecek alanları içeren gövdeyi üretir. */
function govdeUret(form: AyarFormu): { govde: AyarGuncellemesi; hatalar: FormHatalari } {
  const hatalar: FormHatalari = {};
  const markaHatasi = zorunluHatasi(form.marka_adi, "Marka adı");
  if (markaHatasi) hatalar.marka_adi = markaHatasi;

  const saklama = Number(form.saklama_gun);
  if (!Number.isInteger(saklama) || saklama < 1 || saklama > EN_BUYUK_SAKLAMA_GUNU) {
    hatalar.saklama_gun = `Saklama süresi 1 ile ${EN_BUYUK_SAKLAMA_GUNU} gün arasında olmalıdır.`;
  }

  const port = form.smtp_port ? Number(form.smtp_port) : null;
  if (port !== null && (!Number.isInteger(port) || port < 1 || port > 65535)) {
    hatalar.smtp_port = "SMTP portu 1 ile 65535 arasında olmalıdır.";
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

export default function AyarlarSayfasi() {
  const { showToast } = useToast();
  const { veri, yukleniyor, hata, yenile } = useUzakVeri<Ayarlar>(ayarlariGetir, []);
  const [form, setForm] = useState<AyarFormu | null>(null);
  const [hatalar, setHatalar] = useState<FormHatalari>({});
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [kaydetmeHatasi, setKaydetmeHatasi] = useState<string | null>(null);

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
      showToast("Ayarlar kaydedildi.", "success");
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
        <h1 className="text-2xl font-semibold tracking-tight text-neutral-900">Ayarlar</h1>
        <p className="text-sm text-neutral-500">
          Marka, kayıt politikası, SMTP ve bakım modu; değişiklikler denetim izine yazılır.
        </p>
      </header>

      <VeriDurumu yukleniyor={yukleniyor} hata={hata} yenile={yenile}>
        {form && veri ? (
          <div className="flex flex-col gap-6">
            {kaydetmeHatasi ? (
              <Alert tone="danger" title="Ayarlar kaydedilemedi">
                {kaydetmeHatasi}
              </Alert>
            ) : null}

            {form.bakim_modu ? (
              <Alert tone="warning" title="Bakım modu açık">
                Bakım modu açıkken <code>/sohbet</code> ve <code>/sohbet/akis</code> uçları{" "}
                <code>503</code> döner; sohbet geçici olarak kullanılamaz.
              </Alert>
            ) : null}

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Genel</CardTitle>
                <CardDescription>Marka adı ve kayıt politikası.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Field label="Marka adı" error={hatalar.marka_adi} required>
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
                  label="Saklama süresi (gün)"
                  error={hatalar.saklama_gun}
                  hint={`Varsayılan ${VARSAYILAN_SAKLAMA_GUNU} gün; temizleme bu süreyi kullanır.`}
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
                  <Label>Kayıt açık</Label>
                  <Switch
                    checked={form.kayit_acik}
                    onChange={(deger) => guncelle("kayit_acik", deger)}
                    label="Son kullanıcı kaydı kabul edilsin"
                  />
                  <p className="text-xs text-neutral-500">
                    Kapalıyken <code>/kimlik/kayit</code> yeni hesap açmaz.
                  </p>
                </div>

                <div className="flex flex-col gap-3">
                  <Label>Maskeleme</Label>
                  <Switch
                    checked={form.maskeleme_aktif}
                    onChange={(deger) => guncelle("maskeleme_aktif", deger)}
                    label="Kişisel veri maskeleme etkin"
                  />
                  <p className="text-xs text-neutral-500">
                    Maskeleme kayıt anında uygulanır; geçmiş kayıtlar değişmez.
                  </p>
                </div>

                <div className="flex flex-col gap-3 md:col-span-2">
                  <Label>Bakım modu</Label>
                  <Switch
                    checked={form.bakim_modu}
                    onChange={(deger) => guncelle("bakim_modu", deger)}
                    label="Sohbet uçları bakımda"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle>E-posta (SMTP)</CardTitle>
                  <Badge tone={veri.smtp_tanimli ? "success" : "neutral"}>
                    {veri.smtp_tanimli ? "SMTP tanımlı" : "SMTP tanımsız"}
                  </Badge>
                </div>
                <CardDescription>
                  SMTP tanımlı değilken doğrulama ve sıfırlama bağlantıları panelde
                  gösterilir.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Field label="Sunucu" hint="Boş bırakılırsa SMTP kapatılır.">
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
                  label="Port"
                  error={hatalar.smtp_port}
                  hint="Yalnız yazılabilir; boş bırakılırsa değişmez."
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

                <Field label="Kullanıcı" hint="Yalnız yazılabilir; boş bırakılırsa değişmez.">
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

                <Field
                  label="Parola"
                  hint="Boş bırakılırsa mevcut parola değişmez; parola hiçbir zaman görüntülenmez."
                >
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

                <Field label="Gönderen adresi">
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

                <Field label="TLS" hint="Yalnız yazılabilir; seçim yapılmazsa değişmez.">
                  {({ id, ...erisim }) => (
                    <Select
                      id={id}
                      {...erisim}
                      value={form.smtp_tls}
                      onChange={(olay) => guncelle("smtp_tls", olay.target.value as TlsSecimi)}
                    >
                      <option value="degistirme">Değiştirme</option>
                      <option value="acik">Açık</option>
                      <option value="kapali">Kapalı</option>
                    </Select>
                  )}
                </Field>
              </CardContent>
            </Card>

            <div className="flex items-center gap-2">
              <Button loading={kaydediliyor} onClick={() => void kaydet()}>
                <Save aria-hidden className="size-4" />
                Ayarları kaydet
              </Button>
              <Button
                variant="ghost"
                onClick={yenile}
                disabled={kaydediliyor}
              >
                <RefreshCw aria-hidden className="size-4" />
                Sunucudan yenile
              </Button>
            </div>

            <LogTemizlemeKarti saklamaGunu={veri.saklama_gun} onTemizlendi={yenile} />
          </div>
        ) : null}
      </VeriDurumu>
    </div>
  );
}
