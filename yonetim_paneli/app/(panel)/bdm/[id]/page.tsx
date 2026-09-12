"use client";

import { useState } from "react";

import { useParams } from "next/navigation";

import { ArrowLeft } from "lucide-react";

import { bdmGetir, surucuDurumuGetir } from "@/lib/bdm";
import { BDM_DURUMU_ETIKETI, BDM_DURUMU_TONU } from "@/lib/etiketler";
import { useUzakVeri } from "@/lib/kancalar";
import { DugmeBaglantisi } from "@/components/bdm/dugme-baglantisi";
import { GpuSeridi } from "@/components/bdm/gpu-seridi";
import { SekmeCalisma } from "@/components/bdm/sekme-calisma";
import { SekmeGenel } from "@/components/bdm/sekme-genel";
import { SekmeGunlukler } from "@/components/bdm/sekme-gunlukler";
import { SekmeHazirlama } from "@/components/bdm/sekme-hazirlama";
import { SekmeYonlendirme } from "@/components/bdm/sekme-yonlendirme";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs } from "@/components/ui/tabs";

const SEKMELER = [
  { value: "genel", label: "Genel" },
  { value: "hazirlama", label: "Hazırlama" },
  { value: "calisma", label: "Çalışma" },
  { value: "gunlukler", label: "Günlükler" },
  { value: "yonlendirme", label: "Yönlendirme" },
];

/** BDM ayrıntısı: Genel · Hazırlama · Çalışma · Günlükler · Yönlendirme (§12.2). */
export default function BdmDetaySayfasi() {
  const parametreler = useParams<{ id: string }>();
  const id = Number(parametreler.id);
  const [sekme, setSekme] = useState("genel");

  const bdm = useUzakVeri(() => bdmGetir(id), [id]);
  const surucu = useUzakVeri(surucuDurumuGetir, []);

  if (!Number.isInteger(id) || id <= 0) {
    return (
      <Alert tone="danger" title="Geçersiz kayıt">
        <p>Adresteki BDM kimliği geçersiz.</p>
        <DugmeBaglantisi href="/bdm" variant="secondary" className="mt-2">
          Listeye dön
        </DugmeBaglantisi>
      </Alert>
    );
  }

  if (bdm.yukleniyor && !bdm.veri) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (bdm.hata || !bdm.veri) {
    return (
      <div className="flex flex-col gap-4">
        <Alert tone="danger" title="BDM yüklenemedi">
          <p>{bdm.hata ?? "Kayıt bulunamadı."}</p>
        </Alert>
        <div className="flex gap-2">
          <DugmeBaglantisi href="/bdm" variant="secondary">
            <ArrowLeft aria-hidden className="size-4" />
            Listeye dön
          </DugmeBaglantisi>
        </div>
      </div>
    );
  }

  const kayit = bdm.veri;

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight text-neutral-900">
              {kayit.gorunen_ad}
            </h1>
            <Badge tone={BDM_DURUMU_TONU[kayit.durum]}>{BDM_DURUMU_ETIKETI[kayit.durum]}</Badge>
            <Badge tone="neutral">{kayit.yerel_mi ? "Yerel" : "Uzak"}</Badge>
          </div>
          <p className="font-mono text-xs text-neutral-500">
            {kayit.slug} · {kayit.temel_url || "adres tanımsız"} · {kayit.upstream_model || "model tanımsız"}
          </p>
        </div>
        <DugmeBaglantisi href="/bdm" variant="secondary">
          <ArrowLeft aria-hidden className="size-4" />
          Listeye dön
        </DugmeBaglantisi>
      </header>

      <GpuSeridi
        surucu={surucu.veri}
        yukleniyor={surucu.yukleniyor}
        hata={surucu.hata}
        yenile={surucu.yenile}
      />

      <Tabs items={SEKMELER} value={sekme} onValueChange={setSekme} />

      {sekme === "genel" ? (
        <SekmeGenel key={kayit.id} bdm={kayit} onGuncellendi={() => bdm.yenile()} />
      ) : null}
      {sekme === "hazirlama" ? <SekmeHazirlama key={kayit.id} bdm={kayit} /> : null}
      {sekme === "calisma" ? (
        <SekmeCalisma
          key={kayit.id}
          bdm={kayit}
          onDurumDegisti={() => {
            bdm.yenile();
            surucu.yenile();
          }}
        />
      ) : null}
      {sekme === "gunlukler" ? <SekmeGunlukler key={kayit.id} bdm={kayit} /> : null}
      {sekme === "yonlendirme" ? (
        <SekmeYonlendirme key={kayit.id} bdm={kayit} onGuncellendi={() => bdm.yenile()} />
      ) : null}
    </div>
  );
}
