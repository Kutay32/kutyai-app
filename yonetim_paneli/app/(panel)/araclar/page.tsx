"use client";

import { useState } from "react";

import { Wrench } from "lucide-react";

import { ApiHatasi, hataMesaji } from "@/lib/api";
import {
  ARAC_SAYFA_BOYUTLARI,
  BASLANGIC_CAGRI_FILTRESI,
  aracEtkinlikAyarla,
  aracSil,
  araclariGetir,
  cagriSorgusu,
  cagrilariGetir,
  type Arac,
  type AracCagrisi,
  type AracCagrisiDurumu,
  type CagriFiltresi,
} from "@/lib/araclar";
import { useDil } from "@/lib/dil";
import { useUzakVeri } from "@/lib/kancalar";
import { aktifOrganizasyonRolu, organizasyonYazabilirMi } from "@/lib/organizasyonlar";
import { AracDeneDiyalogu } from "@/components/arac/arac-dene-diyalogu";
import { AracDiyalogu } from "@/components/arac/arac-diyalogu";
import { AracTablosu } from "@/components/arac/arac-tablosu";
import { CagriDetayCekmecesi } from "@/components/arac/cagri-detay-cekmecesi";
import { CagriTablosu } from "@/components/arac/cagri-tablosu";
import { Sayfalama } from "@/components/loglar/sayfalama";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";

type EtkinSuzgeci = "tumu" | "etkin" | "pasif";

const CAGRI_DURUMLARI: AracCagrisiDurumu[] = ["basarili", "hata"];

/** Araç yönetimi: tanımlar, çağrı günlüğü, test akışı. */
export default function AraclarSayfasi() {
  const { t } = useDil();
  const { showToast } = useToast();

  const [sekme, setSekme] = useState("araclar");
  const [etkinSuzgeci, setEtkinSuzgeci] = useState<EtkinSuzgeci>("tumu");

  const suzgecDegeri = etkinSuzgeci === "tumu" ? null : etkinSuzgeci === "etkin";
  const araclar = useUzakVeri(() => araclariGetir(suzgecDegeri), [suzgecDegeri]);
  // Çağrı günlüğü süzgeci tüm araçları görsün (pasifler dahil).
  const tumAraclar = useUzakVeri(() => araclariGetir(null), []);
  const aracListesi = araclar.veri ?? [];
  const filtreListesi = tumAraclar.veri ?? [];

  const [cagriFiltresi, setCagriFiltresi] = useState<CagriFiltresi>(BASLANGIC_CAGRI_FILTRESI);
  const cagrilar = useUzakVeri(() => cagrilariGetir(cagriFiltresi), [
    cagriSorgusu(cagriFiltresi),
  ]);
  const cagriListesi = cagrilar.veri?.kayitlar ?? [];

  const [duzenlenen, setDuzenlenen] = useState<Arac | null>(null);
  const [diyalogAcik, setDiyalogAcik] = useState(false);
  const [denenen, setDenenen] = useState<Arac | null>(null);
  const [deneAcik, setDeneAcik] = useState(false);
  const [silinecek, setSilinecek] = useState<Arac | null>(null);
  const [siliniyor, setSiliniyor] = useState(false);
  const [silmeHatasi, setSilmeHatasi] = useState<string | null>(null);
  const [degisenId, setDegisenId] = useState<number | null>(null);
  const [seciliCagri, setSeciliCagri] = useState<AracCagrisi | null>(null);

  const rol = useUzakVeri(aktifOrganizasyonRolu);
  // Araç yazmaları (oluştur/güncelle/sil/dene) sahip/yonetici/operatör ister;
  // rol bilinmiyorsa düğmeler gizlenmez, yetki kararı sunucuda kalır.
  const yazabilir = rol.veri === null || organizasyonYazabilirMi(rol.veri ?? undefined);

  // Silme onayı cümlesi `{baglanti}` ayırıcısıyla parçalanır (araç adı vurgulanır).
  const silmeCumlesi = t("arac.sil.soru").split("{baglanti}");

  const yenile = () => {
    araclar.yenile();
    tumAraclar.yenile();
  };

  const etkinDegistir = async (arac: Arac, etkin: boolean) => {
    setDegisenId(arac.id);
    try {
      await aracEtkinlikAyarla(arac.id, etkin);
      showToast(
        t("arac.etkin.bildirim", {
          ad: arac.ad,
          durum: etkin ? t("arac.etkin.acik") : t("arac.etkin.kapali"),
        }),
        "success",
      );
      yenile();
    } catch (sebep) {
      if (sebep instanceof ApiHatasi && sebep.durum === 404) {
        showToast(t("arac.sil.bulunamadi"), "info");
        yenile();
      } else {
        showToast(`${t("arac.etkin.hata.baslik")}: ${hataMesaji(sebep)}`, "danger");
      }
    } finally {
      setDegisenId(null);
    }
  };

  const sil = async () => {
    if (!silinecek) return;
    setSiliniyor(true);
    setSilmeHatasi(null);
    try {
      await aracSil(silinecek.id);
      showToast(t("arac.sil.bildirim"), "success");
      setSilinecek(null);
      yenile();
      cagrilar.yenile();
    } catch (sebep) {
      if (sebep instanceof ApiHatasi && sebep.durum === 404) {
        showToast(t("arac.sil.bulunamadi"), "info");
        setSilinecek(null);
        yenile();
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
            {t("arac.baslik")}
          </h1>
          <p className="max-w-2xl text-sm text-neutral-500">{t("arac.aciklama")}</p>
        </div>
        {sekme === "araclar" && yazabilir ? (
          <Button
            onClick={() => {
              setDuzenlenen(null);
              setDiyalogAcik(true);
            }}
          >
            {t("arac.yeni")}
          </Button>
        ) : null}
      </header>

      <Tabs
        items={[
          {
            value: "araclar",
            label: t("arac.sekme.araclar"),
            count: araclar.veri ? araclar.veri.length : undefined,
          },
          {
            value: "cagrilar",
            label: t("arac.sekme.cagrilar"),
            count: cagrilar.veri ? cagrilar.veri.toplam : undefined,
          },
        ]}
        value={sekme}
        onValueChange={setSekme}
      />

      {sekme === "araclar" ? (
        <>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[12rem_auto]">
            <Select
              aria-label={t("arac.suzgec.durum")}
              value={etkinSuzgeci}
              onChange={(olay) => setEtkinSuzgeci(olay.target.value as EtkinSuzgeci)}
            >
              <option value="tumu">{t("arac.suzgec.tum")}</option>
              <option value="etkin">{t("arac.suzgec.etkin")}</option>
              <option value="pasif">{t("arac.suzgec.pasif")}</option>
            </Select>
          </div>

          {araclar.hata ? (
            <Alert tone="danger" title={t("arac.liste.alinamadi")}>
              <p>{araclar.hata}</p>
              <Button variant="secondary" size="sm" className="mt-2" onClick={araclar.yenile}>
                {t("arac.yeniden_dene")}
              </Button>
            </Alert>
          ) : null}

          {araclar.yukleniyor ? (
            <div className="flex flex-col gap-2 rounded-lg border border-neutral-200 bg-white p-4">
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : null}

          {!araclar.yukleniyor && !araclar.hata && aracListesi.length === 0 ? (
            <EmptyState
              icon={<Wrench aria-hidden className="size-6" />}
              title={t("arac.bos.baslik")}
              description={t("arac.bos.aciklama")}
              action={
                yazabilir ? (
                  <Button
                    onClick={() => {
                      setDuzenlenen(null);
                      setDiyalogAcik(true);
                    }}
                  >
                    {t("arac.yeni")}
                  </Button>
                ) : undefined
              }
            />
          ) : null}

          {!araclar.yukleniyor && !araclar.hata && aracListesi.length > 0 ? (
            <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
              <div className="overflow-x-auto">
                <AracTablosu
                  araclar={aracListesi}
                  degisenId={degisenId}
                  yazabilir={yazabilir}
                  onEtkinDegistir={(arac, etkin) => void etkinDegistir(arac, etkin)}
                  onDuzenle={(arac) => {
                    setDuzenlenen(arac);
                    setDiyalogAcik(true);
                  }}
                  onDene={(arac) => {
                    setDenenen(arac);
                    setDeneAcik(true);
                  }}
                  onSil={(arac) => {
                    setSilmeHatasi(null);
                    setSilinecek(arac);
                  }}
                />
              </div>
            </div>
          ) : null}
        </>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_1fr_auto]">
            <Select
              aria-label={t("arac.cagri.suzgec.arac")}
              value={cagriFiltresi.arac_id === null ? "" : String(cagriFiltresi.arac_id)}
              onChange={(olay) =>
                setCagriFiltresi((onceki) => ({
                  ...onceki,
                  arac_id: olay.target.value ? Number(olay.target.value) : null,
                  sayfa: 1,
                }))
              }
            >
              <option value="">{t("arac.cagri.suzgec.tum_araclar")}</option>
              {filtreListesi.map((arac) => (
                <option key={arac.id} value={arac.id}>
                  {arac.ad}
                </option>
              ))}
            </Select>

            <Select
              aria-label={t("arac.cagri.suzgec.durum")}
              value={cagriFiltresi.durum}
              onChange={(olay) =>
                setCagriFiltresi((onceki) => ({
                  ...onceki,
                  durum: olay.target.value as AracCagrisiDurumu | "",
                  sayfa: 1,
                }))
              }
            >
              <option value="">{t("arac.cagri.suzgec.tum_durumlar")}</option>
              {CAGRI_DURUMLARI.map((durum) => (
                <option key={durum} value={durum}>
                  {durum === "basarili"
                    ? t("arac.cagri.durum.basarili")
                    : t("arac.cagri.durum.hata")}
                </option>
              ))}
            </Select>

            <Button
              variant="ghost"
              disabled={cagriFiltresi.arac_id === null && cagriFiltresi.durum === ""}
              onClick={() =>
                setCagriFiltresi((onceki) => ({
                  ...BASLANGIC_CAGRI_FILTRESI,
                  boyut: onceki.boyut,
                }))
              }
            >
              {t("arac.cagri.suzgec.temizle")}
            </Button>
          </div>

          {cagrilar.hata ? (
            <Alert tone="danger" title={t("arac.cagri.alinamadi")}>
              <p>{cagrilar.hata}</p>
              <Button variant="secondary" size="sm" className="mt-2" onClick={cagrilar.yenile}>
                {t("arac.yeniden_dene")}
              </Button>
            </Alert>
          ) : null}

          {cagrilar.yukleniyor ? (
            <div className="flex flex-col gap-2 rounded-lg border border-neutral-200 bg-white p-4">
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : null}

          {!cagrilar.yukleniyor && !cagrilar.hata && cagriListesi.length === 0 ? (
            <EmptyState
              title={t("arac.cagri.bos.baslik")}
              description={t("arac.cagri.bos.aciklama")}
            />
          ) : null}

          {!cagrilar.yukleniyor && !cagrilar.hata && cagriListesi.length > 0 ? (
            <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
              <div className="overflow-x-auto">
                <CagriTablosu kayitlar={cagriListesi} onDetay={setSeciliCagri} />
              </div>
              <div className="border-t border-neutral-200">
                <Sayfalama
                  toplam={cagrilar.veri?.toplam ?? 0}
                  sayfa={cagriFiltresi.sayfa}
                  boyut={cagriFiltresi.boyut}
                  boyutlar={ARAC_SAYFA_BOYUTLARI}
                  onSayfa={(sayfa) =>
                    setCagriFiltresi((onceki) => ({ ...onceki, sayfa }))
                  }
                  onBoyut={(boyut) =>
                    setCagriFiltresi((onceki) => ({ ...onceki, boyut, sayfa: 1 }))
                  }
                />
              </div>
            </div>
          ) : null}
        </>
      )}

      <AracDiyalogu
        acik={diyalogAcik}
        arac={duzenlenen}
        onKapat={() => setDiyalogAcik(false)}
        onKaydedildi={(arac) => {
          showToast(
            duzenlenen
              ? t("arac.kaydet.bildirim", { ad: arac.ad })
              : t("arac.olustur.bildirim", { ad: arac.ad }),
            "success",
          );
          yenile();
        }}
      />

      <AracDeneDiyalogu
        acik={deneAcik}
        arac={denenen}
        onKapat={() => setDeneAcik(false)}
        onCalistirildi={() => {
          cagrilar.yenile();
        }}
        onGecmise={() => {
          setDeneAcik(false);
          setSekme("cagrilar");
        }}
      />

      {seciliCagri ? (
        <CagriDetayCekmecesi kayit={seciliCagri} onKapat={() => setSeciliCagri(null)} />
      ) : null}

      <Dialog
        open={silinecek !== null}
        onClose={() => {
          if (!siliniyor) setSilinecek(null);
        }}
        title={t("arac.sil.baslik")}
        description={t("arac.sil.aciklama")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setSilinecek(null)} disabled={siliniyor}>
              {t("arac.vazgec")}
            </Button>
            <Button variant="danger" loading={siliniyor} onClick={() => void sil()}>
              {t("arac.sil.onayla")}
            </Button>
          </>
        }
      >
        {silmeHatasi ? (
          <Alert tone="danger" title={t("arac.sil.hata.baslik")}>
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
