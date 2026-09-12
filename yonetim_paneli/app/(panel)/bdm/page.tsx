"use client";

import { useEffect, useState } from "react";

import { Bot } from "lucide-react";

import { BDM_DURUMU_ETIKETI } from "@/lib/etiketler";
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
          <h1 className="text-xl font-semibold tracking-tight text-neutral-900">BDM'ler</h1>
          <p className="text-sm text-neutral-500">
            Bağlı dil modellerini yönetin, hazırlayın ve çalıştırın.
          </p>
        </div>
        <DugmeBaglantisi href="/bdm/yeni">Yeni BDM</DugmeBaglantisi>
      </header>

      <GpuSeridi
        surucu={surucu.veri}
        yukleniyor={surucu.yukleniyor}
        hata={surucu.hata}
        yenile={surucu.yenile}
      />

      <div className="grid grid-cols-1 gap-2 md:grid-cols-[2fr_1fr_1fr_auto]">
        <Input
          aria-label="BDM ara"
          placeholder="Görünen ad veya slug ara…"
          value={arama}
          onChange={(olay) => setArama(olay.target.value)}
        />
        <Select
          aria-label="Sağlayıcı süzgeci"
          value={saglayiciSuzgeci}
          onChange={(olay) => setSaglayiciSuzgeci(olay.target.value)}
        >
          <option value="">Tüm sağlayıcılar</option>
          {(saglayicilar.veri ?? []).map((bilgi) => (
            <option key={bilgi.ad} value={bilgi.ad}>
              {bilgi.gorunen_ad}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Durum süzgeci"
          value={durumSuzgeci}
          onChange={(olay) => setDurumSuzgeci(olay.target.value)}
        >
          <option value="">Tüm durumlar</option>
          {DURUMLAR.map((durum) => (
            <option key={durum} value={durum}>
              {BDM_DURUMU_ETIKETI[durum]}
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
          Süzgeçleri temizle
        </Button>
      </div>

      {kayitlar.hata ? (
        <Alert tone="danger" title="BDM listesi alınamadı">
          <p>{kayitlar.hata}</p>
          <Button variant="secondary" size="sm" className="mt-2" onClick={kayitlar.yenile}>
            Yeniden dene
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
          title={suzgecEtkin ? "Süzgeçle eşleşen BDM yok." : "Henüz BDM eklenmedi."}
          description={
            suzgecEtkin
              ? "Arama metnini veya süzgeçleri değiştirip yeniden deneyin."
              : "İlk modelinizi ekleyip bağlantısını doğrulayın."
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
                Süzgeçleri temizle
              </Button>
            ) : (
              <DugmeBaglantisi href="/bdm/yeni">Yeni BDM</DugmeBaglantisi>
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
            {suzulmus.length} kayıt gösteriliyor.
          </p>
        </div>
      ) : null}
    </div>
  );
}
