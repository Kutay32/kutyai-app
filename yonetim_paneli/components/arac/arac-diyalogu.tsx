"use client";

import { useEffect, useState } from "react";

import { hataMesaji } from "@/lib/api";
import {
  ARAC_TURLERI,
  YERLESIK_SLUGLAR,
  aracGuncelle,
  aracOlustur,
  type Arac,
  type AracIstegi,
  type AracTuru,
} from "@/lib/araclar";
import { useDil } from "@/lib/dil";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

/** Tür etiketleri katalogdan gelir (spec §10.2). */
const TUR_ANAHTARI = {
  webhook: "arac.tur.webhook",
  yerlesik: "arac.tur.yerlesik",
} as const;

export type AracDiyaloguProps = {
  acik: boolean;
  /** `null` → yeni araç; doluysa kayıt düzenlenir. */
  arac: Arac | null;
  onKapat: () => void;
  onKaydedildi: (arac: Arac) => void;
};

/** JSON alanını nesneye çözer; boş metin `undefined` döner. */
function jsonNesne(metin: string): { deger?: Record<string, unknown>; gecerli: boolean } {
  const temiz = metin.trim();
  if (!temiz) return { gecerli: true };
  try {
    const veri = JSON.parse(temiz) as unknown;
    if (veri === null || typeof veri !== "object" || Array.isArray(veri)) {
      return { gecerli: false };
    }
    return { deger: veri as Record<string, unknown>, gecerli: true };
  } catch {
    return { gecerli: false };
  }
}

/** Araç oluşturma/düzenleme diyaloğu (webhook ve yerleşik türler). */
export function AracDiyalogu({ acik, arac, onKapat, onKaydedildi }: AracDiyaloguProps) {
  const { t } = useDil();

  const [ad, setAd] = useState("");
  const [slug, setSlug] = useState("");
  const [aciklama, setAciklama] = useState("");
  const [tur, setTur] = useState<AracTuru>("webhook");
  const [ucNoktasi, setUcNoktasi] = useState("");
  const [basliklarMetni, setBasliklarMetni] = useState("");
  const [semaMetni, setSemaMetni] = useState("");
  const [etkin, setEtkin] = useState(true);
  const [hatalar, setHatalar] = useState<Record<string, string | null>>({});
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);
  const [kaydediliyor, setKaydediliyor] = useState(false);

  // Diyalog her açılışta seçili aracın değerleriyle kurulur.
  useEffect(() => {
    if (!acik) return;
    setAd(arac?.ad ?? "");
    setSlug(arac?.slug ?? "");
    setAciklama(arac?.aciklama ?? "");
    setTur(arac?.tur ?? "webhook");
    setUcNoktasi(arac?.uc_noktasi ?? "");
    setBasliklarMetni("");
    setSemaMetni(
      arac && Object.keys(arac.json_sema ?? {}).length > 0
        ? JSON.stringify(arac.json_sema, null, 2)
        : "",
    );
    setEtkin(arac?.etkin ?? true);
    setHatalar({});
    setSunucuHatasi(null);
  }, [acik, arac]);

  const kapat = () => {
    onKapat();
    setHatalar({});
    setSunucuHatasi(null);
    setBasliklarMetni("");
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    const bulunan: Record<string, string | null> = {};
    if (ad.trim().length < 2) bulunan.ad = t("arac.form.ad.zorunlu");
    if (tur === "yerlesik" && !slug) bulunan.slug = t("arac.form.yerlesik_slug");
    if (tur === "webhook" && !ucNoktasi.trim()) {
      bulunan.uc = t("arac.form.uc.zorunlu");
    } else if (tur === "webhook" && !/^https?:\/\//i.test(ucNoktasi.trim())) {
      bulunan.uc = t("arac.form.uc.gecersiz");
    }

    const basliklar = jsonNesne(basliklarMetni);
    if (!basliklar.gecerli) bulunan.basliklar = t("arac.form.basliklar.gecersiz");
    const sema = jsonNesne(semaMetni);
    if (!sema.gecerli) bulunan.sema = t("arac.form.sema.gecersiz");

    setHatalar(bulunan);
    if (Object.values(bulunan).some(Boolean)) return;

    const govde: AracIstegi = {
      ad: ad.trim(),
      tur,
      aciklama: aciklama.trim(),
      etkin,
      ...(tur === "yerlesik"
        ? { slug }
        : { slug: slug.trim() || undefined, uc_noktasi: ucNoktasi.trim() }),
      ...(basliklar.deger ? { basliklar: basliklar.deger as Record<string, string> } : {}),
      ...(sema.deger ? { json_sema: sema.deger } : {}),
    };

    setSunucuHatasi(null);
    setKaydediliyor(true);
    try {
      const kayit = arac ? await aracGuncelle(arac.id, govde) : await aracOlustur(govde);
      onKaydedildi(kayit);
      kapat();
    } catch (sebep) {
      setSunucuHatasi(hataMesaji(sebep));
    } finally {
      setKaydediliyor(false);
    }
  };

  const maskeliBasliklar = arac ? Object.entries(arac.basliklar) : [];

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      className="max-h-[90vh] overflow-y-auto"
      title={arac ? t("arac.diyalog.duzenle.baslik") : t("arac.diyalog.yeni.baslik")}
      description={t("arac.diyalog.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={kaydediliyor}>
            {t("arac.vazgec")}
          </Button>
          <Button type="submit" form="arac-formu" loading={kaydediliyor}>
            {arac ? t("arac.form.kaydet") : t("arac.form.olustur")}
          </Button>
        </>
      }
    >
      <form id="arac-formu" onSubmit={gonder} className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("arac.form.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field label={t("arac.form.ad")} hint={t("arac.form.ad.ipucu")} error={hatalar.ad} required>
          {({ id, invalid, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              invalid={invalid}
              value={ad}
              onChange={(olay) => setAd(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("arac.form.tur")}>
          {({ id, invalid, ...erisim }) => (
            <Select
              id={id}
              {...erisim}
              invalid={invalid}
              value={tur}
              onChange={(olay) => {
                const yeni = olay.target.value as AracTuru;
                setTur(yeni);
                if (yeni === "yerlesik") setSlug((onceki) => onceki || YERLESIK_SLUGLAR[0]);
              }}
            >
              {ARAC_TURLERI.map((secenek) => (
                <option key={secenek} value={secenek}>
                  {t(TUR_ANAHTARI[secenek])}
                </option>
              ))}
            </Select>
          )}
        </Field>

        {tur === "yerlesik" ? (
          <Field label={t("arac.form.yerlesik_slug")} error={hatalar.slug} required>
            {({ id, invalid, ...erisim }) => (
              <Select
                id={id}
                {...erisim}
                invalid={invalid}
                value={slug}
                onChange={(olay) => setSlug(olay.target.value)}
              >
                {YERLESIK_SLUGLAR.map((secenek) => (
                  <option key={secenek} value={secenek}>
                    {secenek}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        ) : (
          <>
            <Field label={t("arac.form.slug")} hint={t("arac.form.slug.ipucu")} error={hatalar.slug}>
              {({ id, invalid, ...erisim }) => (
                <Input
                  id={id}
                  {...erisim}
                  invalid={invalid}
                  value={slug}
                  onChange={(olay) => setSlug(olay.target.value)}
                />
              )}
            </Field>

            <Field
              label={t("arac.form.uc")}
              hint={t("arac.form.uc.ipucu")}
              error={hatalar.uc}
              required
            >
              {({ id, invalid, ...erisim }) => (
                <Input
                  id={id}
                  {...erisim}
                  invalid={invalid}
                  type="url"
                  value={ucNoktasi}
                  onChange={(olay) => setUcNoktasi(olay.target.value)}
                />
              )}
            </Field>

            <Field
              label={t("arac.form.basliklar")}
              hint={
                maskeliBasliklar.length > 0
                  ? t("arac.form.basliklar.maskeli.ipucu")
                  : t("arac.form.basliklar.ipucu")
              }
              error={hatalar.basliklar}
            >
              {({ id, invalid, ...erisim }) => (
                <>
                  <Textarea
                    id={id}
                    {...erisim}
                    invalid={invalid}
                    rows={3}
                    value={basliklarMetni}
                    onChange={(olay) => setBasliklarMetni(olay.target.value)}
                  />
                  {maskeliBasliklar.length > 0 ? (
                    <ul className="flex flex-col gap-0.5">
                      {maskeliBasliklar.map(([anahtar, deger]) => (
                        <li key={anahtar} className="font-mono text-xs text-neutral-500">
                          {anahtar}: {deger}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </>
              )}
            </Field>
          </>
        )}

        <Field label={t("arac.form.aciklama")} hint={t("arac.form.aciklama.ipucu")}>
          {({ id, invalid, ...erisim }) => (
            <Textarea
              id={id}
              {...erisim}
              invalid={invalid}
              rows={3}
              value={aciklama}
              onChange={(olay) => setAciklama(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("arac.form.sema")} hint={t("arac.form.sema.ipucu")} error={hatalar.sema}>
          {({ id, invalid, ...erisim }) => (
            <Textarea
              id={id}
              {...erisim}
              invalid={invalid}
              rows={6}
              className="font-mono text-xs"
              value={semaMetni}
              onChange={(olay) => setSemaMetni(olay.target.value)}
            />
          )}
        </Field>

        <Field label={t("arac.form.etkin")}>
          {({ id }) => <Switch id={id} checked={etkin} onChange={setEtkin} />}
        </Field>
      </form>
    </Dialog>
  );
}
