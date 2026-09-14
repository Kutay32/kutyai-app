"use client";

import { useEffect, useState } from "react";

import Link from "next/link";

import { tarihSaatBicimle } from "@/lib/bicim";
import { useDil } from "@/lib/dil";
import { BDM_DURUMU_ANAHTARI, BDM_DURUMU_TONU } from "@/lib/etiketler";
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
  const { t } = useDil();
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
        showToast(t("bdm.bildirim.baslatildi", { ad: bdm.gorunen_ad }), "success");
      } else {
        await bdmDurdur(bdm.id);
        showToast(t("bdm.bildirim.durduruldu", { ad: bdm.gorunen_ad }), "success");
      }
      yenile();
    } catch (hata) {
      showToast(hata instanceof Error ? hata.message : t("bdm.hata.islem"), "danger");
    } finally {
      setIslemdeId(null);
    }
  }

  async function kopyala() {
    if (!kopyalanan) return;
    const hata = zorunluHatasi(kopyaAdi, t("bdm.alan.yeni_ad"));
    setKopyaHatasi(hata);
    if (hata) return;

    setIslemdeId(kopyalanan.id);
    try {
      const yeni = await bdmKopyala(kopyalanan.id, kopyaAdi.trim());
      showToast(t("bdm.bildirim.kopyalandi", { ad: yeni.gorunen_ad }), "success");
      setKopyalanan(null);
      setKopyaAdi("");
      yenile();
    } catch (sebep) {
      setKopyaHatasi(sebep instanceof Error ? sebep.message : t("bdm.hata.kopyalama"));
    } finally {
      setIslemdeId(null);
    }
  }

  async function sil() {
    if (!silinecek) return;
    setIslemdeId(silinecek.id);
    try {
      await bdmSil(silinecek.id);
      showToast(t("bdm.bildirim.silindi", { ad: silinecek.gorunen_ad }), "success");
      setSilinecek(null);
      yenile();
    } catch (sebep) {
      setSilmeHatasi(sebep instanceof Error ? sebep.message : t("bdm.hata.silme"));
    } finally {
      setIslemdeId(null);
    }
  }

  // Silme onayı: kayıt adı cümle içinde vurgulu kalır.
  const silmeParcalari = t("bdm.sil.uyari").split("{ad}");

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("bdm.alan.gorunen_ad")}</TableHead>
            <TableHead>{t("bdm.alan.saglayici")}</TableHead>
            <TableHead>{t("bdm.alan.model")}</TableHead>
            <TableHead>{t("bdm.alan.durum")}</TableHead>
            <TableHead>{t("bdm.alan.yer")}</TableHead>
            <TableHead>{t("bdm.alan.guncellenme")}</TableHead>
            <TableHead className="text-right">{t("bdm.alan.islemler")}</TableHead>
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
                <Badge tone={BDM_DURUMU_TONU[bdm.durum]}>
                  {t(BDM_DURUMU_ANAHTARI[bdm.durum])}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge tone="neutral">{bdm.yerel_mi ? t("bdm.yerel") : t("bdm.uzak")}</Badge>
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
                    setKopyaAdi(t("bdm.kopyala.varsayilan_ad", { ad: bdm.gorunen_ad }));
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
        title={t("bdm.kopyala.baslik")}
        description={
          kopyalanan
            ? t("bdm.kopyala.aciklama", { ad: kopyalanan.gorunen_ad })
            : undefined
        }
        footer={
          <>
            <Button variant="secondary" onClick={() => setKopyalanan(null)}>
              {t("bdm.vazgec")}
            </Button>
            <Button loading={islemdeId === kopyalanan?.id} onClick={() => void kopyala()}>
              {t("bdm.eylem.kopyala")}
            </Button>
          </>
        }
      >
        <Field label={t("bdm.alan.yeni_gorunen_ad")} required error={kopyaHatasi}>
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
        title={t("bdm.sil.baslik")}
        description={t("bdm.sil.aciklama")}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSilinecek(null)}>
              {t("bdm.vazgec")}
            </Button>
            <Button
              variant="danger"
              loading={islemdeId === silinecek?.id}
              onClick={() => void sil()}
            >
              {t("bdm.sil.kalicilik")}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          {silmeHatasi ? <Alert tone="danger">{silmeHatasi}</Alert> : null}
          <p className="text-sm text-neutral-600">
            <span className="font-medium text-neutral-900">
              {silmeParcalari[0]}
              {silinecek?.gorunen_ad}
            </span>
            {silmeParcalari[1]}
          </p>
        </div>
      </Dialog>
    </>
  );
}
