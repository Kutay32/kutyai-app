"use client";

import { useState } from "react";

import { Library } from "lucide-react";

import { ApiHatasi, hataMesaji } from "@/lib/api";
import { bdmListesi, type BdmKaydi } from "@/lib/bdm";
import {
  belgeSil,
  belgeYenidenGom,
  belgeleriGetir,
  type BelgeOzeti,
} from "@/lib/bilgi-tabani";
import { useDil } from "@/lib/dil";
import { dosyalariGetir, type DosyaOzeti } from "@/lib/dosyalar";
import { useUzakVeri } from "@/lib/kancalar";
import { aktifOrganizasyonRolu, organizasyonYazabilirMi } from "@/lib/organizasyonlar";
import { AramaPaneli } from "@/components/bilgi/arama-paneli";
import { BelgeDetayCekmecesi } from "@/components/bilgi/belge-detay-cekmecesi";
import { BelgeEkleDiyalogu } from "@/components/bilgi/belge-ekle-diyalogu";
import { BelgeTablosu } from "@/components/bilgi/belge-tablosu";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";

/** Bilgi tabanı: belge listesi/bakımı ve vektör arama sekmesi. */
export default function BilgiTabaniSayfasi() {
  const { t } = useDil();
  const { showToast } = useToast();

  const [sekme, setSekme] = useState("belgeler");
  const belgeler = useUzakVeri(belgeleriGetir, []);
  const bdmler = useUzakVeri(() => bdmListesi(), []);
  // Belge eklerken dosya seçimi için kayıtlı dosyalar (ilk sayfa yeterli).
  const dosyalar = useUzakVeri(
    () => dosyalariGetir({ arama: "", sayfa: 1, boyut: 100 }),
    [],
  );
  const dosyaListesi: DosyaOzeti[] = dosyalar.veri?.kayitlar ?? [];
  const bdmListesiVerisi: BdmKaydi[] = bdmler.veri ?? [];

  const [eklemeAcik, setEklemeAcik] = useState(false);
  const [secili, setSecili] = useState<BelgeOzeti | null>(null);
  const [silinecek, setSilinecek] = useState<BelgeOzeti | null>(null);
  const [siliniyor, setSiliniyor] = useState(false);
  const [silmeHatasi, setSilmeHatasi] = useState<string | null>(null);
  const [tazelenenId, setTazelenenId] = useState<number | null>(null);

  const rol = useUzakVeri(aktifOrganizasyonRolu);
  // RAG yazmaları (belge ekle/sil/yeniden göm) sahip/yonetici/operatör ister;
  // rol bilinmiyorsa düğmeler gizlenmez, yetki kararı sunucuda kalır.
  const yazabilir = rol.veri === null || organizasyonYazabilirMi(rol.veri ?? undefined);

  const liste = belgeler.veri ?? [];
  // Silme onayı cümlesi `{baglanti}` ayırıcısıyla parçalanır (belge adı vurgulanır).
  const silmeCumlesi = t("bilgi.sil.soru").split("{baglanti}");

  const tazele = async (belge: BelgeOzeti) => {
    setTazelenenId(belge.id);
    try {
      const guncel = await belgeYenidenGom(belge.id);
      showToast(t("bilgi.tazele.bildirim", { sayi: guncel.parca_sayisi }), "success");
      belgeler.yenile();
    } catch (sebep) {
      if (sebep instanceof ApiHatasi && sebep.durum === 404) {
        showToast(t("bilgi.tazele.bulunamadi"), "info");
        belgeler.yenile();
      } else {
        showToast(`${t("bilgi.tazele.hata.baslik")}: ${hataMesaji(sebep)}`, "danger");
      }
    } finally {
      setTazelenenId(null);
    }
  };

  const sil = async () => {
    if (!silinecek) return;
    setSiliniyor(true);
    setSilmeHatasi(null);
    try {
      await belgeSil(silinecek.id);
      showToast(t("bilgi.sil.bildirim"), "success");
      setSilinecek(null);
      belgeler.yenile();
    } catch (sebep) {
      if (sebep instanceof ApiHatasi && sebep.durum === 404) {
        showToast(t("bilgi.sil.bulunamadi"), "info");
        setSilinecek(null);
        belgeler.yenile();
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
            {t("bilgi.baslik")}
          </h1>
          <p className="max-w-2xl text-sm text-neutral-500">{t("bilgi.aciklama")}</p>
        </div>
        {sekme === "belgeler" && yazabilir ? (
          <Button onClick={() => setEklemeAcik(true)}>{t("bilgi.yeni")}</Button>
        ) : null}
      </header>

      <Tabs
        items={[
          {
            value: "belgeler",
            label: t("bilgi.sekme.belgeler"),
            count: belgeler.veri ? belgeler.veri.length : undefined,
          },
          { value: "arama", label: t("bilgi.sekme.arama") },
        ]}
        value={sekme}
        onValueChange={setSekme}
      />

      {sekme === "arama" ? <AramaPaneli bdmler={bdmListesiVerisi} /> : null}

      {sekme === "belgeler" ? (
        <>
          {belgeler.hata ? (
            <Alert tone="danger" title={t("bilgi.liste.alinamadi")}>
              <p>{belgeler.hata}</p>
              <Button variant="secondary" size="sm" className="mt-2" onClick={belgeler.yenile}>
                {t("bilgi.yeniden_dene")}
              </Button>
            </Alert>
          ) : null}

          {belgeler.yukleniyor ? (
            <div className="flex flex-col gap-2 rounded-lg border border-neutral-200 bg-white p-4">
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : null}

          {!belgeler.yukleniyor && !belgeler.hata && liste.length === 0 ? (
            <EmptyState
              icon={<Library aria-hidden className="size-6" />}
              title={t("bilgi.bos.baslik")}
              description={t("bilgi.bos.aciklama")}
              action={
                yazabilir ? (
                  <Button onClick={() => setEklemeAcik(true)}>{t("bilgi.yeni")}</Button>
                ) : undefined
              }
            />
          ) : null}

          {!belgeler.yukleniyor && !belgeler.hata && liste.length > 0 ? (
            <div className="overflow-hidden rounded-lg border border-neutral-200 bg-white">
              <div className="overflow-x-auto">
                <BelgeTablosu
                  kayitlar={liste}
                  tazelenenId={tazelenenId}
                  yazabilir={yazabilir}
                  onDetay={setSecili}
                  onTazele={(belge) => void tazele(belge)}
                  onSil={(belge) => {
                    setSilmeHatasi(null);
                    setSilinecek(belge);
                  }}
                />
              </div>
            </div>
          ) : null}
        </>
      ) : null}

      <BelgeEkleDiyalogu
        acik={eklemeAcik}
        bdmler={bdmListesiVerisi}
        dosyalar={dosyaListesi}
        onKapat={() => setEklemeAcik(false)}
        onEklendi={(belge) => {
          showToast(t("bilgi.ekle.bildirim", { ad: belge.ad }), "success");
          belgeler.yenile();
        }}
      />

      {secili ? (
        <BelgeDetayCekmecesi belge={secili} onKapat={() => setSecili(null)} />
      ) : null}

      <Dialog
        open={silinecek !== null}
        onClose={() => {
          if (!siliniyor) setSilinecek(null);
        }}
        title={t("bilgi.sil.baslik")}
        description={t("bilgi.sil.aciklama")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setSilinecek(null)} disabled={siliniyor}>
              {t("bilgi.vazgec")}
            </Button>
            <Button variant="danger" loading={siliniyor} onClick={() => void sil()}>
              {t("bilgi.sil.onayla")}
            </Button>
          </>
        }
      >
        {silmeHatasi ? (
          <Alert tone="danger" title={t("bilgi.sil.hata.baslik")}>
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
