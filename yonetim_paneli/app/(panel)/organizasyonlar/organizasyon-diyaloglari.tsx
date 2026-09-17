"use client";

import { useState } from "react";

import { useDil } from "@/lib/dil";
import { organizasyonHatasi, organizasyonOlustur } from "@/lib/organizasyonlar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

/** `POST /organizasyonlar` — oluşturan kişi sahip rolüyle eklenir. */
export function OrganizasyonOlusturDiyalogu({
  acik,
  onKapat,
  onOlusturuldu,
}: {
  acik: boolean;
  onKapat: () => void;
  onOlusturuldu: (organizasyonId: number) => void;
}) {
  const { t } = useDil();
  const { showToast } = useToast();
  const [ad, setAd] = useState("");
  const [slug, setSlug] = useState("");
  const [adHata, setAdHata] = useState<string | null>(null);
  const [gonderiliyor, setGonderiliyor] = useState(false);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);

  const kapat = () => {
    onKapat();
    setAd("");
    setSlug("");
    setAdHata(null);
    setSunucuHatasi(null);
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    if (!ad.trim()) {
      setAdHata(t("dogrulama.zorunlu", { alan: t("organizasyon.olustur.ad") }));
      return;
    }
    setAdHata(null);
    setGonderiliyor(true);
    setSunucuHatasi(null);
    try {
      const olusan = await organizasyonOlustur({
        ad: ad.trim(),
        ...(slug.trim() ? { slug: slug.trim() } : {}),
      });
      showToast(t("organizasyon.olustur.basarili", { ad: olusan.ad }), "success");
      onOlusturuldu(olusan.id);
      kapat();
    } catch (sebep) {
      setSunucuHatasi(organizasyonHatasi(sebep));
    } finally {
      setGonderiliyor(false);
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      title={t("organizasyon.olustur.baslik")}
      description={t("organizasyon.olustur.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={gonderiliyor}>
            {t("genel.vazgec")}
          </Button>
          <Button type="submit" form="organizasyon-olustur-formu" loading={gonderiliyor}>
            {t("organizasyon.olustur.gonder")}
          </Button>
        </>
      }
    >
      <form id="organizasyon-olustur-formu" onSubmit={gonder} className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("organizasyon.olustur.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field label={t("organizasyon.olustur.ad")} error={adHata} required>
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

        <Field label={t("organizasyon.olustur.slug")} hint={t("organizasyon.olustur.slug.ipucu")}>
          {({ id, ...erisim }) => (
            <Input
              id={id}
              {...erisim}
              value={slug}
              autoComplete="off"
              onChange={(olay) => setSlug(olay.target.value)}
            />
          )}
        </Field>
      </form>
    </Dialog>
  );
}
