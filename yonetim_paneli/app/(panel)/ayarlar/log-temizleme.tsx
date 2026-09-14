"use client";

import { useState } from "react";

import { Trash2 } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { loglariTemizle } from "@/lib/loglar";
import { TEHLIKELI_GUN_SECENEKLERI } from "@/lib/ayarlar";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

export type LogTemizlemeKartiProps = {
  /** Ayarlardaki saklama süresi; "varsayılan" seçeneğinde kullanılır. */
  saklamaGunu: number;
  onTemizlendi: () => void;
};

/** Saklama süresini aşan kayıtları silen tehlikeli işlem (yalnız yönetici). */
export function LogTemizlemeKarti({ saklamaGunu, onTemizlendi }: LogTemizlemeKartiProps) {
  const { showToast } = useToast();
  const { t } = useDil();
  const [gun, setGun] = useState("");
  const [onayAcik, setOnayAcik] = useState(false);
  const [siliniyor, setSiliniyor] = useState(false);
  const [hata, setHata] = useState<string | null>(null);

  const temizle = async () => {
    setSiliniyor(true);
    setHata(null);
    try {
      const sonuc = await loglariTemizle(gun ? Number(gun) : null);
      showToast(t("ayarlar.log.silindi", { sayi: sonuc.silinen }), "success");
      setOnayAcik(false);
      onTemizlendi();
    } catch (sebep) {
      setHata(hataMesaji(sebep));
    } finally {
      setSiliniyor(false);
    }
  };

  const hedef =
    gun === ""
      ? t("ayarlar.log.hedef.saklama", { gun: saklamaGunu })
      : t("ayarlar.log.hedef.gun", { gun });

  return (
    <>
      <Card className="rounded-2xl border-rose-200">
        <CardHeader>
          <CardTitle className="text-rose-900">{t("ayarlar.log.baslik")}</CardTitle>
          <CardDescription>{t("ayarlar.log.aciklama")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <Field label={t("ayarlar.log.yas")} className="w-full md:w-64">
            {({ id, ...erisim }) => (
              <Select
                id={id}
                {...erisim}
                value={gun}
                onChange={(olay) => setGun(olay.target.value)}
              >
                <option value="">{t("ayarlar.log.saklama_secenegi", { gun: saklamaGunu })}</option>
                {TEHLIKELI_GUN_SECENEKLERI.map((secenek) => (
                  <option key={secenek} value={secenek}>
                    {t("ayarlar.log.gunden_eski", { gun: secenek })}
                  </option>
                ))}
              </Select>
            )}
          </Field>

          <Button
            variant="danger"
            onClick={() => {
              setHata(null);
              setOnayAcik(true);
            }}
          >
            <Trash2 aria-hidden className="size-4" />
            {t("ayarlar.log.temizle")}
          </Button>
        </CardContent>
      </Card>

      <Dialog
        open={onayAcik}
        onClose={() => {
          if (!siliniyor) setOnayAcik(false);
        }}
        title={t("ayarlar.log.temizle")}
        description={t("ayarlar.log.onay.aciklama")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOnayAcik(false)} disabled={siliniyor}>
              {t("genel.vazgec")}
            </Button>
            <Button variant="danger" loading={siliniyor} onClick={() => void temizle()}>
              {t("ayarlar.log.kalici_sil")}
            </Button>
          </>
        }
      >
        {hata ? (
          <Alert tone="danger" title={t("ayarlar.log.hata.baslik")}>
            {hata}
          </Alert>
        ) : (
          <p className="text-sm text-neutral-600">
            {t("ayarlar.log.onay.soru", { hedef })}
          </p>
        )}
      </Dialog>
    </>
  );
}
