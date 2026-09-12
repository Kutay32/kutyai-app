"use client";

import { useEffect, useState } from "react";

import { useRouter } from "next/navigation";

import { Trash2 } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { bdmSil, type BdmKaydi } from "@/lib/bdm";
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
      showToast(`${bdm.gorunen_ad} silindi.`, "success");
      router.replace("/bdm");
    } catch (hata) {
      // Bağlı konuşma/kullanım kaydı varsa 409 gecersiz_gecis döner (§8).
      setSilmeHatasi(hataMesaji(hata));
    } finally {
      setSiliniyor(false);
    }
  }

  const silmeGerekcesi = !yonetici
    ? "Silme yalnız yönetici rolünde yapılabilir."
    : bdm.durum === "calisiyor"
      ? "Çalışan model silinemez; önce durdurun."
      : null;

  return (
    <div className="flex flex-col gap-4">
      <BdmFormu mod="duzenle" baslangic={bdm} onKaydedildi={onGuncellendi} />

      <Card className="border-rose-200">
        <CardHeader>
          <CardTitle>BDM'yi sil</CardTitle>
          <CardDescription>
            Kayıt kalıcı olarak silinir. Bağlı konuşma veya kullanım kaydı varsa silme
            reddedilir ve gerekçe gösterilir.
          </CardDescription>
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
              BDM'yi sil
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
        title="Silmeyi onayla"
        description="Bu işlem geri alınamaz."
        footer={
          <>
            <Button variant="secondary" onClick={() => setOnayAcik(false)}>
              Vazgeç
            </Button>
            <Button variant="danger" loading={siliniyor} onClick={() => void sil()}>
              Kalıcı olarak sil
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          {silmeHatasi ? <Alert tone="danger">{silmeHatasi}</Alert> : null}
          <p className="text-sm text-neutral-600">
            <span className="font-medium text-neutral-900">{bdm.gorunen_ad}</span> (
            <span className="font-mono text-xs">{bdm.slug}</span>) kaydı silinecek.
          </p>
        </div>
      </Dialog>
    </div>
  );
}
