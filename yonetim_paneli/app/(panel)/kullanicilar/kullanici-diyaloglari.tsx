"use client";

import { useState } from "react";

import { TriangleAlert } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { epostaHatasi, parolaHatasi, zorunluHatasi } from "@/lib/dogrulama";
import { KULLANICI_DURUMU_ANAHTARI, ROL_ANAHTARI } from "@/lib/etiketler";
import {
  KULLANICI_DURUMLARI,
  ROLLER,
  geciciParolaUret,
  kullaniciGuncelle,
  kullaniciOlustur,
  kullaniciPasiflestir,
  type KullaniciGuncellemesi,
} from "@/lib/kullanicilar";
import type { Kullanici, KullaniciDurumu, Rol } from "@/lib/tipler";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

type EkleHatalari = { eposta?: string; ad_soyad?: string; parola?: string };

export function PersonelEkleDiyalogu({
  acik,
  onKapat,
  onEklendi,
}: {
  acik: boolean;
  onKapat: () => void;
  onEklendi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [eposta, setEposta] = useState("");
  const [adSoyad, setAdSoyad] = useState("");
  const [parola, setParola] = useState("");
  const [rol, setRol] = useState<Rol>("izleyici");
  const [hatalar, setHatalar] = useState<EkleHatalari>({});
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);
  /** Oluşturma başarılıysa form yerine geçici parolayı gösteren durum. */
  const [olusan, setOlusan] = useState<{ eposta: string; parola: string } | null>(null);

  const kapat = () => {
    onKapat();
    setEposta("");
    setAdSoyad("");
    setParola("");
    setRol("izleyici");
    setHatalar({});
    setSunucuHatasi(null);
    setOlusan(null);
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    const yeni: EkleHatalari = {
      eposta: epostaHatasi(eposta) ?? undefined,
      ad_soyad: zorunluHatasi(adSoyad, t("kullanicilar.ad_soyad")) ?? undefined,
      parola: parolaHatasi(parola) ?? undefined,
    };
    setHatalar(yeni);
    if (yeni.eposta || yeni.ad_soyad || yeni.parola) return;

    setGonderiliyor(true);
    setSunucuHatasi(null);
    try {
      await kullaniciOlustur({
        eposta: eposta.trim(),
        ad_soyad: adSoyad.trim(),
        parola,
        rol,
      });
      setOlusan({ eposta: eposta.trim(), parola });
      onEklendi();
    } catch (sebep) {
      setSunucuHatasi(hataMesaji(sebep));
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      title={olusan ? t("kullanicilar.ekle.basarili.baslik") : t("kullanicilar.ekle.baslik")}
      description={
        olusan
          ? t("kullanicilar.ekle.basarili.aciklama")
          : t("kullanicilar.ekle.aciklama")
      }
      footer={
        olusan ? (
          <Button onClick={kapat}>{t("kullanicilar.ekle.anladim")}</Button>
        ) : (
          <>
            <Button variant="ghost" onClick={kapat} disabled={gonderiliyor}>
              {t("kullanicilar.vazgec")}
            </Button>
            <Button type="submit" form="personel-ekle-formu" loading={gonderiliyor}>
              {t("kullanicilar.ekle.gonder")}
            </Button>
          </>
        )
      }
    >
      {olusan ? (
        <div className="flex flex-col gap-4">
          <Alert tone="warning" title={t("kullanicilar.ekle.parola.uyari.baslik")}>
            {t("kullanicilar.ekle.parola.uyari.metin")}
          </Alert>
          <dl className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                {t("kullanicilar.eposta")}
              </dt>
              <dd className="text-sm text-neutral-900">{olusan.eposta}</dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="text-xs tracking-wide text-neutral-500 uppercase">
                {t("kullanicilar.gecici_parola")}
              </dt>
              <dd className="rounded-lg border border-neutral-200 bg-neutral-50 p-3 font-mono text-sm break-all text-neutral-900 select-all">
                {olusan.parola}
              </dd>
            </div>
          </dl>
        </div>
      ) : (
        <form id="personel-ekle-formu" onSubmit={gonder} className="flex flex-col gap-4">
          {sunucuHatasi ? (
            <Alert tone="danger" title={t("kullanicilar.ekle.hata.baslik")}>
              {sunucuHatasi}
            </Alert>
          ) : null}

          <Field label={t("kullanicilar.eposta")} error={hatalar.eposta} required>
            {({ id, invalid, ...erisim }) => (
              <Input
                id={id}
                {...erisim}
                invalid={invalid}
                type="email"
                autoComplete="off"
                value={eposta}
                onChange={(olay) => setEposta(olay.target.value)}
              />
            )}
          </Field>

          <Field label={t("kullanicilar.ad_soyad")} error={hatalar.ad_soyad} required>
            {({ id, invalid, ...erisim }) => (
              <Input
                id={id}
                {...erisim}
                invalid={invalid}
                value={adSoyad}
                onChange={(olay) => setAdSoyad(olay.target.value)}
              />
            )}
          </Field>

          <Field
            label={t("kullanicilar.gecici_parola")}
            error={hatalar.parola}
            hint={t("kullanicilar.ekle.parola.ipucu")}
            required
          >
            {({ id, invalid, ...erisim }) => (
              <div className="flex items-center gap-2">
                <Input
                  id={id}
                  {...erisim}
                  invalid={invalid}
                  value={parola}
                  onChange={(olay) => setParola(olay.target.value)}
                />
                <Button
                  variant="secondary"
                  onClick={() => setParola(geciciParolaUret())}
                  className="shrink-0"
                >
                  {t("kullanicilar.ekle.parola.uret")}
                </Button>
              </div>
            )}
          </Field>

          <Field label={t("kullanicilar.rol")}>
            {({ id, ...erisim }) => (
              <Select
                id={id}
                {...erisim}
                value={rol}
                onChange={(olay) => setRol(olay.target.value as Rol)}
              >
                {ROLLER.map((secenek) => (
                  <option key={secenek} value={secenek}>
                    {t(ROL_ANAHTARI[secenek])}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </form>
      )}
    </Dialog>
  );
}

export function KullaniciDuzenleDiyalogu({
  kullanici,
  onKapat,
  onKaydedildi,
}: {
  kullanici: Kullanici;
  onKapat: () => void;
  onKaydedildi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [adSoyad, setAdSoyad] = useState(kullanici.ad_soyad);
  const [rol, setRol] = useState<Rol>(kullanici.rol);
  const [durum, setDurum] = useState<KullaniciDurumu>(kullanici.durum);
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const kaydet = async () => {
    const degisiklikler: KullaniciGuncellemesi = {};
    if (adSoyad.trim() !== kullanici.ad_soyad) degisiklikler.ad_soyad = adSoyad.trim();
    if (rol !== kullanici.rol) degisiklikler.rol = rol;
    if (durum !== kullanici.durum) degisiklikler.durum = durum;

    if (Object.keys(degisiklikler).length === 0) {
      showToast(t("kullanicilar.duzenle.degisiklik_yok"), "info");
      onKapat();
      return;
    }

    setKaydediliyor(true);
    setHata(null);
    try {
      await kullaniciGuncelle(kullanici.id, degisiklikler);
      showToast(t("kullanicilar.duzenle.basarili"), "success");
      onKaydedildi();
      onKapat();
    } catch (sebep) {
      setHata(hataMesaji(sebep));
    } finally {
      setKaydediliyor(false);
    }
  };

  return (
    <Dialog
      open
      onClose={() => {
        if (!kaydediliyor) onKapat();
      }}
      title={t("kullanicilar.duzenle.baslik")}
      description={kullanici.eposta}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={kaydediliyor}>
            {t("kullanicilar.vazgec")}
          </Button>
          <Button loading={kaydediliyor} onClick={() => void kaydet()}>
            {t("kullanicilar.kaydet")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {hata ? (
          <Alert tone="danger" title={t("kullanicilar.duzenle.hata.baslik")}>
            {hata}
          </Alert>
        ) : null}

        <Field label={t("kullanicilar.ad_soyad")}>
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              value={adSoyad}
              onChange={(olay) => setAdSoyad(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("kullanicilar.rol")}>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={rol}
              onChange={(olay) => setRol(olay.target.value as Rol)}
            >
              {ROLLER.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {t(ROL_ANAHTARI[secenek])}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label={t("kullanicilar.durum")}>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={durum}
              onChange={(olay) => setDurum(olay.target.value as KullaniciDurumu)}
            >
              {KULLANICI_DURUMLARI.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {t(KULLANICI_DURUMU_ANAHTARI[secenek])}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
    </Dialog>
  );
}

export function PasiflestirDiyalogu({
  kullanici,
  onKapat,
  onPasiflestirildi,
}: {
  kullanici: Kullanici;
  onKapat: () => void;
  onPasiflestirildi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [isleniyor, setIsleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const pasiflestir = async () => {
    setIsleniyor(true);
    setHata(null);
    try {
      await kullaniciPasiflestir(kullanici.id);
      showToast(t("kullanicilar.pasiflestir.basarili", { eposta: kullanici.eposta }), "success");
      onPasiflestirildi();
      onKapat();
    } catch (sebep) {
      // Ör. kendi hesabını pasifleştirme denemesi → 409; sunucu mesajı gösterilir.
      setHata(hataMesaji(sebep));
    } finally {
      setIsleniyor(false);
    }
  };

  const [pasiflestirmeOnce, pasiflestirmeSonra] = t("kullanicilar.pasiflestir.metin").split(
    "{baglanti}",
  );

  return (
    <Dialog
      open
      onClose={() => {
        if (!isleniyor) onKapat();
      }}
      title={t("kullanicilar.pasiflestir.baslik")}
      description={t("kullanicilar.pasiflestir.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={isleniyor}>
            {t("kullanicilar.vazgec")}
          </Button>
          <Button variant="danger" loading={isleniyor} onClick={() => void pasiflestir()}>
            {t("kullanicilar.pasiflestir")}
          </Button>
        </>
      }
    >
      {hata ? (
        <Alert tone="danger" title={t("kullanicilar.pasiflestir.hata.baslik")}>
          {hata}
        </Alert>
      ) : (
        <div className="flex items-start gap-2 text-sm text-neutral-600">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-amber-600" />
          <p>
            {pasiflestirmeOnce}
            <span className="font-medium text-neutral-900">{kullanici.eposta}</span>
            {pasiflestirmeSonra}
          </p>
        </div>
      )}
    </Dialog>
  );
}
