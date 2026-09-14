"use client";

import { useEffect, useState } from "react";

import { Eraser, Pause, Play, RotateCcw } from "lucide-react";

import { hataMesaji } from "@/lib/api";
import { gunlukAkisi, type BdmKaydi } from "@/lib/bdm";
import { useDil } from "@/lib/dil";
import { TerminalLog } from "@/components/bdm/terminal-log";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";

/** Gösterilen en fazla günlük satırı; akış sınırsız olduğu için tampon sınırlanır. */
const EN_FAZLA_SATIR = 2000;

export type SekmeGunluklerProps = { bdm: BdmKaydi };

/** Günlükler sekmesi: konteyner günlüklerini SSE ile canlı gösterir (§11). */
export function SekmeGunlukler({ bdm }: SekmeGunluklerProps) {
  const { t } = useDil();
  const [satirlar, setSatirlar] = useState<string[]>([]);
  const [duraklatildi, setDuraklatildi] = useState(false);
  const [hata, setHata] = useState<string | null>(null);
  const [otomatikKaydir, setOtomatikKaydir] = useState(true);
  const [akisDurumu, setAkisDurumu] = useState<
    "baglaniyor" | "canli" | "duraklatildi" | "bitti"
  >("baglaniyor");
  const [sayac, setSayac] = useState(0);

  useEffect(() => {
    if (duraklatildi) {
      setAkisDurumu("duraklatildi");
      return;
    }
    const denetleyici = new AbortController();
    let iptal = false;

    void (async () => {
      setAkisDurumu("baglaniyor");
      setHata(null);
      let ilkSatir = true;
      try {
        for await (const satir of gunlukAkisi(bdm.id, 200, denetleyici.signal)) {
          if (iptal) return;
          if (ilkSatir) {
            ilkSatir = false;
            setAkisDurumu("canli");
          }
          setSatirlar((onceki) => {
            const yeni = [...onceki, satir];
            return yeni.length > EN_FAZLA_SATIR ? yeni.slice(-EN_FAZLA_SATIR) : yeni;
          });
        }
        // Akış sunucu tarafında kapandı (ör. Ollama sürücüsünde tek satır).
        if (!iptal) setAkisDurumu("bitti");
      } catch (sebep) {
        if (iptal || (sebep instanceof DOMException && sebep.name === "AbortError")) return;
        setHata(hataMesaji(sebep));
        setAkisDurumu("bitti");
      }
    })();

    return () => {
      iptal = true;
      denetleyici.abort();
    };
  }, [bdm.id, duraklatildi, sayac]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("bdm.gunluk.baslik")}</CardTitle>
        <CardDescription>{t("bdm.gunluk.aciklama")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            tone={
              akisDurumu === "canli"
                ? "success"
                : akisDurumu === "duraklatildi"
                  ? "warning"
                  : "neutral"
            }
          >
            {akisDurumu === "canli"
              ? t("bdm.gunluk.durum.canli")
              : akisDurumu === "duraklatildi"
                ? t("bdm.gunluk.durum.duraklatildi")
                : akisDurumu === "bitti"
                  ? t("bdm.gunluk.durum.kapandi")
                  : t("bdm.gunluk.durum.baglaniyor")}
          </Badge>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setDuraklatildi((onceki) => !onceki)}
          >
            {duraklatildi ? (
              <Play aria-hidden className="size-4" />
            ) : (
              <Pause aria-hidden className="size-4" />
            )}
            {duraklatildi ? t("bdm.gunluk.surdur") : t("bdm.gunluk.duraklat")}
          </Button>
          {akisDurumu === "bitti" && !duraklatildi ? (
            <Button variant="secondary" size="sm" onClick={() => setSayac((onceki) => onceki + 1)}>
              <RotateCcw aria-hidden className="size-4" />
              {t("bdm.gunluk.yeniden_baglan")}
            </Button>
          ) : null}
          <Button variant="ghost" size="sm" onClick={() => setSatirlar([])}>
            <Eraser aria-hidden className="size-4" />
            {t("bdm.gunluk.temizle")}
          </Button>
          <Switch
            id="gunluk-otomatik-kaydir"
            checked={otomatikKaydir}
            onChange={setOtomatikKaydir}
            label={t("bdm.gunluk.otomatik_kaydir")}
          />
          <span className="ml-auto text-xs text-neutral-500">
            {t("bdm.gunluk.satir_sayisi", { sayi: satirlar.length })}
          </span>
        </div>

        {hata ? <Alert tone="danger">{hata}</Alert> : null}

        <TerminalLog satirlar={satirlar} otomatikKaydir={otomatikKaydir} />
      </CardContent>
    </Card>
  );
}
