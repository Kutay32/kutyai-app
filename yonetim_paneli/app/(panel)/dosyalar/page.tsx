"use client";

import { useEffect, useState } from "react";

import { FolderOpen } from "lucide-react";

import { ApiHatasi, hataMesaji } from "@/lib/api";
import { useDil } from "@/lib/dil";
import {
  BASLANGIC_DOSYA_FILTRESI,
  DOSYA_SAYFA_BOYUTLARI,
  dosyaIcerikIndir,
  dosyaSil,
  dosyaSorgusu,
  dosyalariGetir,
  type DosyaFiltresi,
  type DosyaOzeti,
} from "@/lib/dosyalar";
import { useUzakVeri } from "@/lib/kancalar";
import { DosyaDetayCekmecesi } from "@/components/dosya/dosya-detay-cekmecesi";
import { DosyaTablosu } from "@/components/dosya/dosya-tablosu";
import { DosyaYukleDiyalogu } from "@/components/dosya/dosya-yukle-diyalogu";
import { Sayfalama } from "@/components/loglar/sayfalama";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast";

/** Dosya listesi: arama, sayfalama, yükleme, indirme, ayrıntı ve silme. */
export default function DosyalarSayfasi() {
  const { t } = useDil();
  const { showToast } = useToast();

  const [filtre, setFiltre] = useState<DosyaFiltresi>(BASLANGIC_DOSYA_FILTRESI);
  const [arama, setArama] = useState("");
  const [gecikmisArama, setGecikmisArama] = useState("");

  // Her tuşta istek atmamak için arama 300 ms geciktirilir (loglar deseni).
  useEffect(() => {
    const zamanlayici = window.setTimeout(() => setGecikmisArama(arama), 300);
    return () => window.clearTimeout(zamanlayici);
  }, [arama]);

  useEffect(() => {
    setFiltre((onceki) =>
      onceki.arama === gecikmisArama ? onceki : { ...onceki, arama: gecikmisArama, sayfa: 1 },
    );
  }, [gecikmisArama]);

  const kayitlar = useUzakVeri(() => dosyalariGetir(filtre), [dosyaSorgusu(filtre)]);
  const liste = kayitlar.veri?.kayitlar ?? [];
  const toplam = kayitlar.veri?.toplam ?? 0;
  // Silme onayı cümlesi `{baglanti}` ayırıcısıyla parçalanır (dosya adı vurgulanır).
  const silmeCumlesi = t("dosya.sil.soru").split("{baglanti}");

  const [yuklemeAcik, setYuklemeAcik] = useState(false);
  const [secili, setSecili] = useState<DosyaOzeti | null>(null);
  const [silinecek, setSilinecek] = useState<DosyaOzeti | null>(null);
  const [siliniyor, setSiliniyor] = useState(false);
  const [silmeHatasi, setSilmeHatasi] = useState<string | null>(null);
  const [indirilenId, setIndirilenId] = useState<number | null>(null);

  const indir = async (dosya: DosyaOzeti) => {
    setIndirilenId(dosya.id);
    try {
      await dosyaIcerikIndir(dosya);
      showToast(t("dosya.indir.bildirim", { ad: dosya.ad }), "success");
    } catch (sebep) {
      showToast(hataMesaji(sebep), "danger");
    } finally {
      setIndirilenId(null);
    }
  };

  const sil = async () => {
    if (!silinecek) return;
    setSiliniyor(true);
    setSilmeHatasi(null);
    try {
      await dosyaSil(silinecek.id);
      showToast(t("dosya.sil.bildirim"), "success");
      setSilinecek(null);
      // Son kayıt silindiyse boş sayfada kalınmasın.
      if (liste.length === 1 && filtre.sayfa > 1) {
        setFiltre((onceki) => ({ ...onceki, sayfa: onceki.sayfa - 1 }));
      } else {
        kayitlar.yenile();
      }
    } catch (sebep) {
      // Başka organizasyonun kaydı `404` döner: hata olarak değil, bilgi olarak göster.
      if (sebep instanceof ApiHatasi && sebep.durum === 404) {
        showToast(t("dosya.sil.bulunamadi"), "info");
        setSilinecek(null);
        kayitlar.yenile();
      } else {
        setSilmeHatasi(hataMesaji(sebep));
      }
    } finally {
      setSiliniyor(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight text-neutral-900">
            {t("dosya.baslik")}
          </h1>
          <p className="max-w-2xl text-sm text-neutral-500">{t("dosya.aciklama")}</p>
        </div>
        <Button onClick={() => setYuklemeAcik(true)}>{t("dosya.yeni")}</Button>
      </header>

      <Input
        aria-label={t("dosya.ara.etiket")}
        placeholder={t("dosya.ara.ipucu")}
        value={arama}
        onChange={(olay) => setArama(olay.target.value)}
      />

      {kayitlar.hata ? (
        <Alert tone="danger" title={t("dosya.liste.alinamadi")}>
          <p>{kayitlar.hata}</p>
          <Button variant="secondary" size="sm" className="mt-2" onClick={kayitlar.yenile}>
            {t("dosya.yeniden_dene")}
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

      {!kayitlar.yukleniyor && !kayitlar.hata && liste.length === 0 ? (
        <EmptyState
          icon={<FolderOpen aria-hidden className="size-6" />}
          title={t("dosya.bos.baslik")}
          description={
            filtre.arama.trim() ? t("dosya.bos.suzgec.aciklama") : t("dosya.bos.aciklama")
          }
          action={<Button onClick={() => setYuklemeAcik(true)}>{t("dosya.yeni")}</Button>}
        />
      ) : null}

      {!kayitlar.yukleniyor && !kayitlar.hata && liste.length > 0 ? (
        <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
          <div className="overflow-x-auto">
            <DosyaTablosu
              kayitlar={liste}
              indirilenId={indirilenId}
              onIndir={(dosya) => void indir(dosya)}
              onDetay={setSecili}
              onSil={(dosya) => {
                setSilmeHatasi(null);
                setSilinecek(dosya);
              }}
            />
          </div>
          <div className="border-t border-neutral-200">
            <Sayfalama
              toplam={toplam}
              sayfa={filtre.sayfa}
              boyut={filtre.boyut}
              boyutlar={DOSYA_SAYFA_BOYUTLARI}
              onSayfa={(sayfa) => setFiltre((onceki) => ({ ...onceki, sayfa }))}
              onBoyut={(boyut) => setFiltre((onceki) => ({ ...onceki, boyut, sayfa: 1 }))}
            />
          </div>
        </div>
      ) : null}

      <DosyaYukleDiyalogu
        acik={yuklemeAcik}
        onKapat={() => setYuklemeAcik(false)}
        onYuklendi={(dosya) => {
          showToast(t("dosya.yukle.bildirim", { ad: dosya.ad }), "success");
          kayitlar.yenile();
        }}
      />

      {secili ? (
        <DosyaDetayCekmecesi dosya={secili} onKapat={() => setSecili(null)} />
      ) : null}

      <Dialog
        open={silinecek !== null}
        onClose={() => {
          if (!siliniyor) setSilinecek(null);
        }}
        title={t("dosya.sil.baslik")}
        description={t("dosya.sil.aciklama")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setSilinecek(null)} disabled={siliniyor}>
              {t("dosya.vazgec")}
            </Button>
            <Button variant="danger" loading={siliniyor} onClick={() => void sil()}>
              {t("dosya.sil.onayla")}
            </Button>
          </>
        }
      >
        {silmeHatasi ? (
          <Alert tone="danger" title={t("dosya.sil.hata.baslik")}>
            {silmeHatasi}
          </Alert>
        ) : silinecek ? (
          <p className="text-sm text-neutral-600">
            {silmeCumlesi[0]}
            <span className="font-medium text-neutral-900">{silinecek.ad}</span>
            {silmeCumlesi[1]}
          </p>
        ) : null}
      </Dialog>
    </div>
  );
}
