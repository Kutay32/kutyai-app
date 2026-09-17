"use client";

import { useState } from "react";

import { useDil } from "@/lib/dil";
import {
  SSO_TURLERI,
  SSO_TURU_ANAHTARI,
  bosAyarlar,
  doluAyarlar,
  saglayiciGuncelle,
  saglayiciOlustur,
  saglayiciSil,
  ssoHatasi,
  turAlanlari,
  type SsoAlani,
  type SsoGuncellemesi,
  type SsoOlusturma,
  type SsoSaglayici,
  type SsoTuru,
} from "@/lib/sso";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/toast";

type AlanHatalari = Record<string, string | undefined>;

/** Sağlayıcı türüne göre `ayarlar` alanları (`sso_oidc.py` / `sso_saml.py`). */
function SaglayiciAlanlari({
  tur,
  ayarlar,
  hatalar,
  devredisi,
  onDegistir,
}: {
  tur: SsoTuru;
  ayarlar: Record<string, string>;
  hatalar: AlanHatalari;
  devredisi: boolean;
  onDegistir: (anahtar: string, deger: string) => void;
}) {
  const { t } = useDil();

  return (
    <>
      {turAlanlari(tur).map((alan: SsoAlani) => (
        <Field
          key={alan.anahtar}
          label={t(alan.etiket)}
          hint={alan.ipucu ? t(alan.ipucu) : undefined}
          error={hatalar[alan.anahtar] ?? null}
          required={alan.zorunlu}
        >
          {({ id, invalid, ...erisim }) =>
            alan.cok_satirli ? (
              <Textarea
                id={id}
                {...erisim}
                rows={6}
                className="font-mono text-xs"
                value={ayarlar[alan.anahtar] ?? ""}
                disabled={devredisi}
                onChange={(olay) => onDegistir(alan.anahtar, olay.target.value)}
              />
            ) : (
              <Input
                id={id}
                {...erisim}
                invalid={invalid}
                autoComplete="off"
                value={ayarlar[alan.anahtar] ?? ""}
                disabled={devredisi}
                onChange={(olay) => onDegistir(alan.anahtar, olay.target.value)}
              />
            )
          }
        </Field>
      ))}
    </>
  );
}

function eksikAlanlar(
  tur: SsoTuru,
  ayarlar: Record<string, string>,
  mesajUret: (alan: SsoAlani) => string,
): AlanHatalari {
  const hatalar: AlanHatalari = {};
  for (const alan of turAlanlari(tur)) {
    if (alan.zorunlu && !(ayarlar[alan.anahtar] ?? "").trim()) {
      hatalar[alan.anahtar] = mesajUret(alan);
    }
  }
  return hatalar;
}

/** `POST /sso/saglayicilar`. */
export function SaglayiciOlusturDiyalogu({
  acik,
  onKapat,
  onOlusturuldu,
}: {
  acik: boolean;
  onKapat: () => void;
  onOlusturuldu: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [tur, setTur] = useState<SsoTuru>("oidc");
  const [ad, setAd] = useState("");
  const [slug, setSlug] = useState("");
  const [etkin, setEtkin] = useState(true);
  const [ayarlar, setAyarlar] = useState<Record<string, string>>(() => bosAyarlar("oidc"));
  const [sir, setSir] = useState("");
  const [adHata, setAdHata] = useState<string | null>(null);
  const [alanHatalari, setAlanHatalari] = useState<AlanHatalari>({});
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);

  const kapat = () => {
    onKapat();
    setTur("oidc");
    setAd("");
    setSlug("");
    setEtkin(true);
    setAyarlar(bosAyarlar("oidc"));
    setSir("");
    setAdHata(null);
    setAlanHatalari({});
    setSunucuHatasi(null);
  };

  const turDegistir = (yeni: SsoTuru) => {
    setTur(yeni);
    setAyarlar(bosAyarlar(yeni));
    setAlanHatalari({});
  };

  const gonder = async () => {
    if (!ad.trim()) {
      setAdHata(t("sso.ad.zorunlu"));
      return;
    }
    const eksikler = eksikAlanlar(tur, ayarlar, (alan) =>
      t("dogrulama.zorunlu", { alan: t(alan.etiket) }),
    );
    setAlanHatalari(eksikler);
    if (Object.keys(eksikler).length > 0) return;

    const girdi: SsoOlusturma = {
      tur,
      ad: ad.trim(),
      etkin,
      ayarlar: doluAyarlar(ayarlar),
      ...(slug.trim() ? { slug: slug.trim() } : {}),
      ...(sir.trim() ? { sir: sir.trim() } : {}),
    };

    setGonderiliyor(true);
    setSunucuHatasi(null);
    try {
      const olusan = await saglayiciOlustur(girdi);
      showToast(t("sso.olustur.basarili", { ad: olusan.ad }), "success");
      onOlusturuldu();
      kapat();
    } catch (sebep) {
      setSunucuHatasi(ssoHatasi(sebep));
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      title={t("sso.olustur.baslik")}
      description={t("sso.olustur.aciklama")}
      className="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={gonderiliyor}>
            {t("genel.vazgec")}
          </Button>
          <Button loading={gonderiliyor} onClick={() => void gonder()}>
            {t("sso.olustur.gonder")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("sso.olustur.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field label={t("sso.tablo.tur")} hint={t("sso.tur.ipucu")} required>
          {({ id, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              value={tur}
              disabled={gonderiliyor}
              onChange={(olay) => turDegistir(olay.target.value as SsoTuru)}
            >
              {SSO_TURLERI.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {t(SSO_TURU_ANAHTARI[secenek])}
                </option>
              ))}
            </Select>
          )}
        </Field>

        <Field label={t("sso.ad")} error={adHata} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              value={ad}
              disabled={gonderiliyor}
              onChange={(olay) => setAd(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("sso.slug")} hint={t("sso.slug.ipucu")}>
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              autoComplete="off"
              value={slug}
              disabled={gonderiliyor}
              onChange={(olay) => setSlug(olay.target.value)}
            />
          )}
        </Field>

        <Field
          label={t("sso.sir")}
          hint={`${t("sso.sir.uyari")} ${t("sso.duzenle.sir.ipucu")}`}
        >
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              type="password"
              autoComplete="new-password"
              value={sir}
              disabled={gonderiliyor}
              onChange={(olay) => setSir(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("sso.etkin.anahtar")} hint={t("sso.olustur.etkin.ipucu")}>
          {({ id }) => (
            <Switch id={id} checked={etkin} onChange={setEtkin} disabled={gonderiliyor} />
          )}
        </Field>

        <SaglayiciAlanlari
          tur={tur}
          ayarlar={ayarlar}
          hatalar={alanHatalari}
          devredisi={gonderiliyor}
          onDegistir={(anahtar, deger) =>
            setAyarlar((onceki) => ({ ...onceki, [anahtar]: deger }))
          }
        />
      </div>
    </Dialog>
  );
}

/** `PATCH /sso/saglayicilar/{id}` — yalnız değişen alanlar gönderilir. */
export function SaglayiciDuzenleDiyalogu({
  saglayici,
  onKapat,
  onKaydedildi,
}: {
  saglayici: SsoSaglayici;
  onKapat: () => void;
  onKaydedildi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [ad, setAd] = useState(saglayici.ad);
  const [etkin, setEtkin] = useState(saglayici.etkin);
  const [ayarlar, setAyarlar] = useState<Record<string, string>>({
    ...bosAyarlar(saglayici.tur),
    ...saglayici.ayarlar,
  });
  const [sir, setSir] = useState("");
  const [adHata, setAdHata] = useState<string | null>(null);
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);

  const kaydet = async () => {
    if (!ad.trim()) {
      setAdHata(t("sso.ad.zorunlu"));
      return;
    }
    setAdHata(null);

    const ayarlarDegisikligi: Record<string, string> = {};
    for (const alan of turAlanlari(saglayici.tur)) {
      const yeni = (ayarlar[alan.anahtar] ?? "").trim();
      const eski = (saglayici.ayarlar[alan.anahtar] ?? "").trim();
      if (yeni && yeni !== eski) ayarlarDegisikligi[alan.anahtar] = yeni;
    }

    const degisiklikler: SsoGuncellemesi = {};
    if (ad.trim() !== saglayici.ad) degisiklikler.ad = ad.trim();
    if (etkin !== saglayici.etkin) degisiklikler.etkin = etkin;
    if (Object.keys(ayarlarDegisikligi).length > 0) degisiklikler.ayarlar = ayarlarDegisikligi;
    if (sir.trim()) degisiklikler.sir = sir.trim();

    if (Object.keys(degisiklikler).length === 0) {
      showToast(t("sso.duzenle.degisiklik_yok"), "info");
      onKapat();
      return;
    }

    setKaydediliyor(true);
    setSunucuHatasi(null);
    try {
      await saglayiciGuncelle(saglayici.id, degisiklikler);
      showToast(t("sso.duzenle.basarili"), "success");
      onKaydedildi();
      onKapat();
    } catch (sebep) {
      setSunucuHatasi(ssoHatasi(sebep));
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
      title={t("sso.duzenle.baslik", { ad: saglayici.ad })}
      description={`${t(SSO_TURU_ANAHTARI[saglayici.tur])} · ${saglayici.slug}`}
      className="max-w-2xl"
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={kaydediliyor}>
            {t("genel.vazgec")}
          </Button>
          <Button loading={kaydediliyor} onClick={() => void kaydet()}>
            {t("organizasyon.bilgi.kaydet")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("sso.duzenle.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field label={t("sso.ad")} error={adHata} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              value={ad}
              disabled={kaydediliyor}
              onChange={(olay) => setAd(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("sso.etkin.anahtar")}>
          {({ id }) => (
            <Switch id={id} checked={etkin} onChange={setEtkin} disabled={kaydediliyor} />
          )}
        </Field>

        <Field
          label={t("sso.sir")}
          hint={
            saglayici.sir_tanimli
              ? `${t("sso.duzenle.sir.tanimli.ipucu")} ${t("sso.duzenle.sir.ipucu")}`
              : `${t("sso.sir.uyari")} ${t("sso.duzenle.sir.ipucu")}`
          }
        >
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              type="password"
              autoComplete="new-password"
              placeholder={saglayici.sir_tanimli ? t("sso.sir.tanimli") : t("sso.sir.tanimsiz")}
              value={sir}
              disabled={kaydediliyor}
              onChange={(olay) => setSir(olay.target.value)}
            />
          )}
        </Field>

        <SaglayiciAlanlari
          tur={saglayici.tur}
          ayarlar={ayarlar}
          hatalar={{}}
          devredisi={kaydediliyor}
          onDegistir={(anahtar, deger) =>
            setAyarlar((onceki) => ({ ...onceki, [anahtar]: deger }))
          }
        />
      </div>
    </Dialog>
  );
}

/** `DELETE /sso/saglayicilar/{id}`. */
export function SaglayiciSilDiyalogu({
  saglayici,
  onKapat,
  onSilindi,
}: {
  saglayici: SsoSaglayici;
  onKapat: () => void;
  onSilindi: () => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [isleniyor, setIsleniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const sil = async () => {
    setIsleniyor(true);
    setHata(null);
    try {
      await saglayiciSil(saglayici.id);
      showToast(t("sso.sil.basarili", { ad: saglayici.ad }), "success");
      onSilindi();
      onKapat();
    } catch (sebep) {
      setHata(ssoHatasi(sebep));
    } finally {
      setIsleniyor(false);
    }
  };

  const [once, sonra] = t("sso.sil.metin").split("{baglanti}");

  return (
    <Dialog
      open
      onClose={() => {
        if (!isleniyor) onKapat();
      }}
      title={t("sso.sil.baslik")}
      description={t("sso.sil.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={onKapat} disabled={isleniyor}>
            {t("genel.vazgec")}
          </Button>
          <Button variant="danger" loading={isleniyor} onClick={() => void sil()}>
            {t("sso.sil.onay")}
          </Button>
        </>
      }
    >
      {hata ? (
        <Alert tone="danger" title={t("sso.sil.hata.baslik")}>
          {hata}
        </Alert>
      ) : (
        <p className="text-sm text-neutral-600">
          {once}
          <span className="font-medium text-neutral-900">{saglayici.ad}</span>
          {sonra}
        </p>
      )}
    </Dialog>
  );
}
