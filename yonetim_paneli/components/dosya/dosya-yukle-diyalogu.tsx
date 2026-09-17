"use client";

import { useState } from "react";

import { Upload } from "lucide-react";

import { hataMesaji, ApiHatasi } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { boyutBicimle, dosyaYukle, type DosyaDetayi } from "@/lib/dosyalar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export type DosyaYukleDiyaloguProps = {
  acik: boolean;
  onKapat: () => void;
  onYuklendi: (dosya: DosyaDetayi) => void;
};

/** Multipart yükleme diyaloğu; sunucu MIME/boyut denetimini uygular. */
export function DosyaYukleDiyalogu({ acik, onKapat, onYuklendi }: DosyaYukleDiyaloguProps) {
  const { t } = useDil();
  const [secilen, setSecilen] = useState<File | null>(null);
  const [alanHatasi, setAlanHatasi] = useState<string | null>(null);
  const [sunucuHatasi, setSunucuHatasi] = useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);

  const kapat = () => {
    onKapat();
    setSecilen(null);
    setAlanHatasi(null);
    setSunucuHatasi(null);
  };

  const gonder = async (olay: React.FormEvent<HTMLFormElement>) => {
    olay.preventDefault();
    if (!secilen) {
      setAlanHatasi(t("dosya.yukle.zorunlu"));
      return;
    }
    setAlanHatasi(null);
    setSunucuHatasi(null);
    setYukleniyor(true);
    try {
      const olusan = await dosyaYukle(secilen);
      onYuklendi(olusan);
      kapat();
    } catch (sebep) {
      // 413 `dosya_cok_buyuk` ve 400 `dosya_tur_desteklenmiyor` sunucudan
      // yerelleştirilmiş mesajla gelir.
      setSunucuHatasi(
        sebep instanceof ApiHatasi && sebep.durum === 413
          ? `${hataMesaji(sebep)} (${boyutBicimle(secilen.size)})`
          : hataMesaji(sebep),
      );
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <Dialog
      open={acik}
      onClose={kapat}
      title={t("dosya.yukle.baslik")}
      description={t("dosya.yukle.aciklama")}
      footer={
        <>
          <Button variant="ghost" onClick={kapat} disabled={yukleniyor}>
            {t("dosya.vazgec")}
          </Button>
          <Button type="submit" form="dosya-yukle-formu" loading={yukleniyor}>
            <Upload aria-hidden className="size-4" />
            {t("dosya.yukle.gonder")}
          </Button>
        </>
      }
    >
      <form id="dosya-yukle-formu" onSubmit={gonder} className="flex flex-col gap-4">
        {sunucuHatasi ? (
          <Alert tone="danger" title={t("dosya.yukle.hata.baslik")}>
            {sunucuHatasi}
          </Alert>
        ) : null}

        <Field label={t("dosya.yukle.dosya")} hint={t("dosya.yukle.ipucu")} error={alanHatasi} required>
          {({ id, invalid, ...erisim }) => (
            <>
              <Input
                id={id}
                {...erisim}
                invalid={invalid}
                type="file"
                onChange={(olay) => {
                  setSecilen(olay.target.files?.[0] ?? null);
                  setAlanHatasi(null);
                }}
              />
              {secilen ? (
                <p className="text-xs text-neutral-500">
                  {t("dosya.yukle.secili", {
                    ad: `${secilen.name} (${boyutBicimle(secilen.size)})`,
                  })}
                </p>
              ) : null}
            </>
          )}
        </Field>
      </form>
    </Dialog>
  );
}
