"use client";

import { useEffect, useState } from "react";

import { Bot } from "lucide-react";

import { useDil } from "@/lib/dil";
import { BDM_DURUMU_ANAHTARI } from "@/lib/etiketler";
import { useUzakVeri } from "@/lib/kancalar";
import { bdmListesi, saglayicilariGetir, surucuDurumuGetir } from "@/lib/bdm";
import type { BdmDurumu } from "@/lib/tipler";
import { BdmTablosu } from "@/components/bdm/bdm-tablosu";
import { DugmeBaglantisi } from "@/components/bdm/dugme-baglantisi";
import { GpuSeridi } from "@/components/bdm/gpu-seridi";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const DURUMLAR: BdmDurumu[] = ["taslak", "hazir", "calisiyor", "durdu", "hata"];

/** BDM listesi: arama, sağlayıcı/durum süzgeci ve satır işlemleri. */
export default function BdmListesiSayfasi() {
  const { t } = useDil();
  const [arama, setArama] = useState("");
  const [gecikmisArama, setGecikmisArama] = useState("");
  const [saglayiciSuzgeci, setSaglayiciSuzgeci] = useState("");
  const [durumSuzgeci, setDurumSuzgeci] = useState("");

  // Yazarken her tuşta istek atmamak için arama 300 ms geciktirilir.
  useEffect(() => {
    const zamanlayici = window.setTimeout(() => setGecikmisArama(arama), 300);
    return () => window.clearTimeout(zamanlayici);
  }, [arama]);

  const kayitlar = useUzakVeri(() => bdmListesi(gecikmisArama), [gecikmisArama]);
  const saglayicilar = useUzakVeri(saglayicilariGetir, []);
  const surucu = useUzakVeri(surucuDurumuGetir, []);

  const suzulmus = (kayitlar.veri ?? []).filter(
    (bdm) =>
      (saglayiciSuzgeci === "" || bdm.saglayici === saglayiciSuzgeci) &&
      (durumSuzgeci === "" || bdm.durum === durumSuzgeci),
  );
  const suzgecEtkin = arama !== "" || saglayiciSuzgeci !== "" || durumSuzgeci !== "";

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight text-neutral-900">{t("bdm.baslik")}</h1>
          <p className="text-sm text-neutral-500">{t("bdm.aciklama")}</p>
        </div>
        <DugmeBaglantisi href="/bdm/yeni">{t("bdm.yeni")}</DugmeBaglantisi>
      </header>

      <GpuSeridi
        surucu={surucu.veri}
        yukleniyor={surucu.yukleniyor}
        hata={surucu.hata}
        yenile={surucu.yenile}
      />

      <div className="grid grid-cols-1 gap-2 md:grid-cols-[2fr_1fr_1fr_auto]">
        <Input
          aria-label={t("bdm.ara.etiket")}
          placeholder={t("bdm.ara.ipucu")}
          value={arama}
          onChange={(olay) => setArama(olay.target.value)}
        />
        <Select
          aria-label={t("bdm.suzgec.saglayici")}
          value={saglayiciSuzgeci}
          onChange={(olay) => setSaglayiciSuzgeci(olay.target.value)}
        >
          <option value="">{t("bdm.suzgec.tum_saglayicilar")}</option>
          {(saglayicilar.veri ?? []).map((bilgi) => (
            <option key={bilgi.ad} value={bilgi.ad}>
              {bilgi.gorunen_ad}
            </option>
          ))}
        </Select>
        <Select
          aria-label={t("bdm.suzgec.durum")}
          value={durumSuzgeci}
          onChange={(olay) => setDurumSuzgeci(olay.target.value)}
        >
          <option value="">{t("bdm.suzgec.tum_durumlar")}</option>
          {DURUMLAR.map((durum) => (
            <option key={durum} value={durum}>
              {t(BDM_DURUMU_ANAHTARI[durum])}
            </option>
          ))}
        </Select>
        <Button
          variant="ghost"
          disabled={!suzgecEtkin}
          onClick={() => {
            setArama("");
            setGecikmisArama("");
            setSaglayiciSuzgeci("");
            setDurumSuzgeci("");
          }}
        >
          {t("bdm.suzgec.temizle")}
        </Button>
      </div>

      {kayitlar.hata ? (
        <Alert tone="danger" title={t("bdm.liste.alinamadi")}>
          <p>{kayitlar.hata}</p>
          <Button variant="secondary" size="sm" className="mt-2" onClick={kayitlar.yenile}>
            {t("bdm.yeniden_dene")}
          </Button>
        </Alert>
      ) : null}

      {kayitlar.yukleniyor ? (
        <div className="flex flex-col gap-2 rounded-lg border border-neutral-200 bg-white p-4">
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : null}

      {!kayitlar.yukleniyor && !kayitlar.hata && suzulmus.length === 0 ? (
        <EmptyState
          icon={<Bot aria-hidden className="size-6" />}
          title={suzgecEtkin ? t("bdm.bos.suzgec.baslik") : t("bdm.bos.baslik")}
          description={
            suzgecEtkin ? t("bdm.bos.suzgec.aciklama") : t("bdm.bos.aciklama")
          }
          action={
            suzgecEtkin ? (
              <Button
                variant="secondary"
                onClick={() => {
                  setArama("");
                  setGecikmisArama("");
                  setSaglayiciSuzgeci("");
                  setDurumSuzgeci("");
                }}
              >
                {t("bdm.suzgec.temizle")}
              </Button>
            ) : (
              <DugmeBaglantisi href="/bdm/yeni">{t("bdm.yeni")}</DugmeBaglantisi>
            )
          }
        />
      ) : null}

      {!kayitlar.yukleniyor && !kayitlar.hata && suzulmus.length > 0 ? (
        <div className="flex flex-col gap-2">
          <BdmTablosu
            kayitlar={suzulmus}
            saglayicilar={saglayicilar.veri ?? []}
            surucu={surucu.veri}
            yenile={() => {
              kayitlar.yenile();
              surucu.yenile();
            }}
          />
          <p className="text-xs text-neutral-500" role="status">
            {t("bdm.kayit.sayisi", { sayi: suzulmus.length })}
          </p>
        </div>
      ) : null}
    </div>
  );
}
