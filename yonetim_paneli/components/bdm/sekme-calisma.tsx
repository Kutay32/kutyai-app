"use client";

import { useCallback, useEffect, useState } from "react";

import { Play, RotateCcw, Square } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import {
  baslatilabilir,
  bdmBaslat,
  bdmDurdur,
  bdmDurumGetir,
  bdmSaglikGetir,
  bdmYenidenBaslat,
  durdurulabilir,
  gpuEngeli,
  surucuDurumuGetir,
  type BdmKaydi,
  type DurumYaniti,
  type SaglikYaniti,
} from "@/lib/bdm";
import { useDil } from "@/lib/dil";
import { BDM_DURUMU_ANAHTARI, BDM_DURUMU_TONU } from "@/lib/etiketler";
import { useUzakVeri } from "@/lib/kancalar";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { useToast } from "@/components/ui/toast";

/** Durumun sekme görünürken yoklanma aralığı (ms). */
const YOKLAMA_ARALIGI = 10_000;

export type SekmeCalismaProps = {
  bdm: BdmKaydi;
  /** BDM kaydı (durum alanı) değiştiğinde üst sayfayı tazeler. */
  onDurumDegisti: () => void;
};

/** Çalışma sekmesi: başlat/durdur/yeniden başlat, durum ve sağlık yoklaması (§11). */
export function SekmeCalisma({ bdm, onDurumDegisti }: SekmeCalismaProps) {
  const { showToast } = useToast();
  const { dil, t } = useDil();
  const surucu = useUzakVeri(surucuDurumuGetir, []);

  const [durum, setDurum] = useState<DurumYaniti | null>(null);
  const [saglik, setSaglik] = useState<SaglikYaniti | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [sonYoklama, setSonYoklama] = useState<string | null>(null);
  const [islem, setIslem] = useState<string | null>(null);
  const [eylemHatasi, setEylemHatasi] = useState<string | null>(null);
  const [sayac, setSayac] = useState(0);

  const yokla = useCallback(async () => {
    if (document.visibilityState !== "visible") return;
    try {
      const [yeniDurum, yeniSaglik] = await Promise.all([
        bdmDurumGetir(bdm.id),
        bdmSaglikGetir(bdm.id),
      ]);
      setDurum(yeniDurum);
      setSaglik(yeniSaglik);
      setHata(null);
      setSonYoklama(new Date().toLocaleTimeString(dil === "tr" ? "tr-TR" : "en-US"));
    } catch (sebep) {
      setHata(hataMesaji(sebep));
    } finally {
      setYukleniyor(false);
    }
  }, [bdm.id, dil]);

  useEffect(() => {
    let iptal = false;
    void yokla();
    const zamanlayici = window.setInterval(() => {
      if (!iptal) void yokla();
    }, YOKLAMA_ARALIGI);
    const gorunurluk = () => {
      if (!iptal && document.visibilityState === "visible") void yokla();
    };
    document.addEventListener("visibilitychange", gorunurluk);
    return () => {
      iptal = true;
      window.clearInterval(zamanlayici);
      document.removeEventListener("visibilitychange", gorunurluk);
    };
  }, [yokla, sayac]);

  async function eylemCalistir(eylem: "baslat" | "durdur" | "yeniden-baslat") {
    setIslem(eylem);
    setEylemHatasi(null);
    try {
      if (eylem === "baslat") await bdmBaslat(bdm.id);
      else if (eylem === "durdur") await bdmDurdur(bdm.id);
      else await bdmYenidenBaslat(bdm.id);
      showToast(t("bdm.bildirim.islem_tamam"), "success");
      setSayac((onceki) => onceki + 1);
      onDurumDegisti();
    } catch (sebep) {
      // 409 gecersiz_gecis gibi durum makinesi hataları burada gösterilir (§11).
      setEylemHatasi(hataMesaji(sebep));
    } finally {
      setIslem(null);
    }
  }

  const engel = gpuEngeli(bdm.saglayici, surucu.veri);
  const aktifDurum = durum?.durum ?? bdm.durum;
  const baslatilir = baslatilabilir(aktifDurum);
  const durdurulur = durdurulabilir(aktifDurum);
  const yenidenBaslatilir = aktifDurum === "calisiyor" || aktifDurum === "durdu";
  const saglikTonu = saglik?.hazir ? "success" : saglik?.calisiyor ? "info" : "neutral";

  return (
    <div className="flex flex-col gap-4">
      {eylemHatasi ? <Alert tone="danger">{eylemHatasi}</Alert> : null}
      {hata ? (
        <Alert tone="warning" title={t("bdm.calisma.durum_okunamadi")}>
          <p>{hata}</p>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("bdm.calisma.baslik")}</CardTitle>
          <CardDescription>{t("bdm.calisma.aciklama")}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
            <StatCard
              label={t("bdm.alan.durum")}
              value={t(BDM_DURUMU_ANAHTARI[durum?.durum ?? bdm.durum])}
              hint={
                sonYoklama
                  ? t("bdm.calisma.son_yoklama", { zaman: sonYoklama })
                  : yukleniyor
                    ? t("bdm.calisma.yoklaniyor")
                    : undefined
              }
            />
            <StatCard
              label={t("bdm.alan.konteyner")}
              value={durum?.konteyner_id ?? bdm.konteyner?.konteyner_id ?? "—"}
            />
            <StatCard
              label={t("bdm.alan.saglik")}
              value={
                saglik?.hazir
                  ? t("bdm.saglik.hazir")
                  : saglik?.calisiyor
                    ? t("bdm.saglik.ayakta")
                    : t("bdm.saglik.kapali")
              }
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-700">
            <span>{t("bdm.calisma.rozet")}</span>
            <Badge tone={BDM_DURUMU_TONU[durum?.durum ?? bdm.durum]}>
              {t(BDM_DURUMU_ANAHTARI[durum?.durum ?? bdm.durum])}
            </Badge>
            <Badge tone={saglikTonu}>
              {saglik?.mesaj ?? t("bdm.calisma.saglik_bekleniyor")}
            </Badge>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              loading={islem === "baslat"}
              disabled={!baslatilir || engel !== null}
              title={engel ?? undefined}
              onClick={() => void eylemCalistir("baslat")}
            >
              <Play aria-hidden className="size-4" />
              {t("bdm.eylem.baslat")}
            </Button>
            <Button
              variant="secondary"
              loading={islem === "durdur"}
              disabled={!durdurulur}
              onClick={() => void eylemCalistir("durdur")}
            >
              <Square aria-hidden className="size-4" />
              {t("bdm.eylem.durdur")}
            </Button>
            <Button
              variant="secondary"
              loading={islem === "yeniden-baslat"}
              disabled={!yenidenBaslatilir || engel !== null}
              title={engel ?? undefined}
              onClick={() => void eylemCalistir("yeniden-baslat")}
            >
              <RotateCcw aria-hidden className="size-4" />
              {t("bdm.eylem.yeniden_baslat")}
            </Button>
          </div>

          {engel ? (
            <Alert tone="warning" title={t("bdm.calisma.gpu_gerekli")}>
              <p>{engel}</p>
              <p>{t("bdm.calisma.gpu_devredisi")}</p>
            </Alert>
          ) : null}

          {!baslatilir && !durdurulur && !engel ? (
            <p className="text-xs text-neutral-500">{t("bdm.calisma.baslatilamaz")}</p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
