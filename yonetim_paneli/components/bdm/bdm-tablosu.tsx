"use client";

import { useEffect, useState } from "react";

import Link from "next/link";

import { tarihSaatBicimle } from "@/lib/bicim";
import { BDM_DURUMU_ETIKETI, BDM_DURUMU_TONU } from "@/lib/etiketler";
import {
  bdmBaslat,
  bdmDurdur,
  bdmKopyala,
  bdmSil,
  gpuEngeli,
  type BdmKaydi,
} from "@/lib/bdm";
import type { SaglayiciBilgisi, SurucuDurumu } from "@/lib/tipler";
import { kullaniciOku } from "@/lib/oturum";
import { SatirMenusu } from "@/components/bdm/satir-menusu";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { zorunluHatasi } from "@/lib/dogrulama";

export type BdmTablosuProps = {
  kayitlar: BdmKaydi[];
  saglayicilar: SaglayiciBilgisi[];
  surucu: SurucuDurumu | null;
  /** Satır işlemi sonrası liste ve durum bilgisi yeniden yüklenir. */
  yenile: () => void;
};

/** BDM listesi tablosu ve satır işlemleri (kopyala, çalıştır/durdur, sil). */
export function BdmTablosu({ kayitlar, saglayicilar, surucu, yenile }: BdmTablosuProps) {
  const { showToast } = useToast();
  const [yonetici, setYonetici] = useState(false);
  const [islemdeId, setIslemdeId] = useState<number | null>(null);
  const [kopyalanan, setKopyalanan] = useState<BdmKaydi | null>(null);
  const [kopyaAdi, setKopyaAdi] = useState("");
  const [kopyaHatasi, setKopyaHatasi] = useState<string | null>(null);
  const [silinecek, setSilinecek] = useState<BdmKaydi | null>(null);
  const [silmeHatasi, setSilmeHatasi] = useState<string | null>(null);

  // Rol yalnız tarayıcıda okunur (sunucu render'ında localStorage yoktur).
  useEffect(() => {
    setYonetici(kullaniciOku()?.rol === "yonetici");
  }, []);

  async function durumEylemi(bdm: BdmKaydi, eylem: "baslat" | "durdur") {
    setIslemdeId(bdm.id);
    try {
      if (eylem === "baslat") {
        await bdmBaslat(bdm.id);
        showToast(`${bdm.gorunen_ad} başlatıldı.`, "success");
      } else {
        await bdmDurdur(bdm.id);
        showToast(`${bdm.gorunen_ad} durduruldu.`, "success");
      }
      yenile();
    } catch (hata) {
      showToast(hata instanceof Error ? hata.message : "İşlem tamamlanamadı.", "danger");
    } finally {
      setIslemdeId(null);
    }
  }

  async function kopyala() {
    if (!kopyalanan) return;
    const hata = zorunluHatasi(kopyaAdi, "Yeni ad");
    setKopyaHatasi(hata);
    if (hata) return;

    setIslemdeId(kopyalanan.id);
    try {
      const yeni = await bdmKopyala(kopyalanan.id, kopyaAdi.trim());
      showToast(`${yeni.gorunen_ad} kopyalandı.`, "success");
      setKopyalanan(null);
      setKopyaAdi("");
      yenile();
    } catch (sebep) {
      setKopyaHatasi(sebep instanceof Error ? sebep.message : "Kopyalama tamamlanamadı.");
    } finally {
      setIslemdeId(null);
    }
  }

  async function sil() {
    if (!silinecek) return;
    setIslemdeId(silinecek.id);
    try {
      await bdmSil(silinecek.id);
      showToast(`${silinecek.gorunen_ad} silindi.`, "success");
      setSilinecek(null);
      yenile();
    } catch (sebep) {
      setSilmeHatasi(sebep instanceof Error ? sebep.message : "Silme tamamlanamadı.");
    } finally {
      setIslemdeId(null);
    }
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Görünen ad</TableHead>
            <TableHead>Sağlayıcı</TableHead>
            <TableHead>Model</TableHead>
            <TableHead>Durum</TableHead>
            <TableHead>Yer</TableHead>
            <TableHead>Güncellenme</TableHead>
            <TableHead className="text-right">İşlemler</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {kayitlar.map((bdm) => (
            <TableRow key={bdm.id}>
              <TableCell>
                <span className="flex flex-col">
                  <Link
                    href={`/bdm/${bdm.id}`}
                    className="font-medium text-neutral-900 underline-offset-2 hover:underline focus:outline-none focus:border-neutral-900 focus:ring-0"
                  >
                    {bdm.gorunen_ad}
                  </Link>
                  <span className="font-mono text-xs text-neutral-500">{bdm.slug}</span>
                </span>
              </TableCell>
              <TableCell>
                {saglayicilar.find((bilgi) => bilgi.ad === bdm.saglayici)?.gorunen_ad ??
                  bdm.saglayici}
              </TableCell>
              <TableCell className="font-mono text-xs">
                {bdm.upstream_model || "—"}
              </TableCell>
              <TableCell>
                <Badge tone={BDM_DURUMU_TONU[bdm.durum]}>{BDM_DURUMU_ETIKETI[bdm.durum]}</Badge>
              </TableCell>
              <TableCell>
                <Badge tone="neutral">{bdm.yerel_mi ? "Yerel" : "Uzak"}</Badge>
              </TableCell>
              <TableCell className="text-sm text-neutral-500">
                {tarihSaatBicimle(bdm.guncellenme)}
              </TableCell>
              <TableCell className="text-right">
                <SatirMenusu
                  bdm={bdm}
                  yonetici={yonetici}
                  gpuGerekcesi={gpuEngeli(bdm.saglayici, surucu)}
                  islemde={islemdeId === bdm.id}
                  onKopyala={() => {
                    setKopyalanan(bdm);
                    setKopyaAdi(`${bdm.gorunen_ad} kopya`);
                    setKopyaHatasi(null);
                  }}
                  onDurum={(eylem) => void durumEylemi(bdm, eylem)}
                  onSil={() => {
                    setSilinecek(bdm);
                    setSilmeHatasi(null);
                  }}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog
        open={kopyalanan !== null}
        onClose={() => setKopyalanan(null)}
        title="BDM'yi kopyala"
        description={
          kopyalanan
            ? `${kopyalanan.gorunen_ad} ayarları yeni bir taslak kayıt olarak çoğaltılır.`
            : undefined
        }
        footer={
          <>
            <Button variant="secondary" onClick={() => setKopyalanan(null)}>
              Vazgeç
            </Button>
            <Button loading={islemdeId === kopyalanan?.id} onClick={() => void kopyala()}>
              Kopyala
            </Button>
          </>
        }
      >
        <Field label="Yeni görünen ad" required error={kopyaHatasi}>
          {(props) => (
            <Input
              {...props}
              invalid={props.invalid}
              value={kopyaAdi}
              onChange={(olay) => {
                setKopyaAdi(olay.target.value);
                setKopyaHatasi(null);
              }}
            />
          )}
        </Field>
      </Dialog>

      <Dialog
        open={silinecek !== null}
        onClose={() => setSilinecek(null)}
        title="BDM'yi sil"
        description="Bu işlem geri alınamaz."
        footer={
          <>
            <Button variant="secondary" onClick={() => setSilinecek(null)}>
              Vazgeç
            </Button>
            <Button
              variant="danger"
              loading={islemdeId === silinecek?.id}
              onClick={() => void sil()}
            >
              Kalıcı olarak sil
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          {silmeHatasi ? <Alert tone="danger">{silmeHatasi}</Alert> : null}
          <p className="text-sm text-neutral-600">
            <span className="font-medium text-neutral-900">{silinecek?.gorunen_ad}</span> kaydı
            ve konteyner kaydı silinir. Bağlı konuşma veya kullanım kaydı varsa silme
            reddedilir.
          </p>
        </div>
      </Dialog>
    </>
  );
}
