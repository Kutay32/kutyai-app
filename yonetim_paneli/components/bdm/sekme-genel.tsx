"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { Trash2 } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { bdmSil, type BdmKaydi } from "@/lib/bdm";
import { useDil } from "@/lib/dil";
import { kullaniciOku } from "@/lib/oturum";
import { BdmFormu } from "@/components/bdm/bdm-formu";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";

export type SekmeGenelProps = {
  bdm: BdmKaydi;
  onGuncellendi: (bdm: BdmKaydi) => void;
};

/** Genel sekmesi: model alanları, maskeli anahtar ve silme (API.md §8). */
export function SekmeGenel({ bdm, onGuncellendi }: SekmeGenelProps) {
  const router = useRouter();
  const { showToast } = useToast();
  const { t } = useDil();
  const [yonetici, setYonetici] = useState(false);
  const [onayAcik, setOnayAcik] = useState(false);
  const [siliniyor, setSiliniyor] = useState(false);
  const [silmeHatasi, setSilmeHatasi] = useState<string | null>(null);

  useEffect(() => {
    setYonetici(kullaniciOku()?.rol === "yonetici");
  }, []);

  async function sil() {
    setSiliniyor(true);
    setSilmeHatasi(null);
    try {
      await bdmSil(bdm.id);
      showToast(t("bdm.bildirim.silindi", { ad: bdm.gorunen_ad }), "success");
      router.replace("/bdm");
    } catch (hata) {
      // Bağlı konuşma/kullanım kaydı varsa 409 gecersiz_gecis döner (§8).
      setSilmeHatasi(hataMesaji(hata));
    } finally {
      setSiliniyor(false);
    }
  }

  const silmeGerekcesi = !yonetici
    ? t("bdm.menu.sil_yetki")
    : bdm.durum === "calisiyor"
      ? t("bdm.menu.sil_calisiyor")
      : null;

  // Silme onayı: kayıt adı ve slug cümle içinde vurgulu/kod biçiminde kalır.
  const onayParcalari = t("bdm.sil.onay.uyari").split(/(\{ad\}|\{slug\})/);

  return (
    <div className="flex flex-col gap-4">
      <BdmFormu mod="duzenle" baslangic={bdm} onKaydedildi={onGuncellendi} />

      <Card className="border-rose-200">
        <CardHeader>
          <CardTitle>{t("bdm.sil.baslik")}</CardTitle>
          <CardDescription>{t("bdm.sil.kart.aciklama")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div>
            <Button
              variant="danger"
              disabled={silmeGerekcesi !== null}
              title={silmeGerekcesi ?? undefined}
              onClick={() => {
                setSilmeHatasi(null);
                setOnayAcik(true);
              }}
            >
              <Trash2 aria-hidden className="size-4" />
              {t("bdm.sil.baslik")}
            </Button>
          </div>
          {silmeGerekcesi ? (
            <p className="text-xs text-neutral-500">{silmeGerekcesi}</p>
          ) : null}
        </CardContent>
      </Card>

      <Dialog
        open={onayAcik}
        onClose={() => setOnayAcik(false)}
        title={t("bdm.sil.onay.baslik")}
        description={t("bdm.sil.aciklama")}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOnayAcik(false)}>
              {t("bdm.vazgec")}
            </Button>
            <Button variant="danger" loading={siliniyor} onClick={() => void sil()}>
              {t("bdm.sil.kalicilik")}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          {silmeHatasi ? <Alert tone="danger">{silmeHatasi}</Alert> : null}
          <p className="text-sm text-neutral-600">
            {onayParcalari.map((parca, sira) => {
              if (parca === "{ad}") {
                return (
                  <span key={sira} className="font-medium text-neutral-900">
                    {bdm.gorunen_ad}
                  </span>
                );
              }
              if (parca === "{slug}") {
                return (
                  <span key={sira} className="font-mono text-xs">
                    {bdm.slug}
                  </span>
                );
              }
              return parca;
            })}
          </p>
        </div>
      </Dialog>
    </div>
  );
}
