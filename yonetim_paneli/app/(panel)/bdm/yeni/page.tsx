"use client";

import { useRouter } from "next/navigation";

import { ArrowLeft } from "lucide-react";

import { BdmFormu } from "@/components/bdm/bdm-formu";
import { DugmeBaglantisi } from "@/components/bdm/dugme-baglantisi";

/** Yeni BDM kaydı: sağlayıcıya göre uyarlanan form (POST /bdm). */
export default function YeniBdmSayfasi() {
  const router = useRouter();

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold tracking-tight text-neutral-900">Yeni BDM</h1>
          <p className="text-sm text-neutral-500">
            Kayıt taslak durumunda oluşturulur; bağlantıyı doğrulayınca hazır olur.
          </p>
        </div>
        <DugmeBaglantisi href="/bdm" variant="secondary">
          <ArrowLeft aria-hidden className="size-4" />
          Listeye dön
        </DugmeBaglantisi>
      </header>

      <BdmFormu
        mod="yeni"
        onKaydedildi={(kayit) => router.replace(`/bdm/${kayit.id}`)}
      />
    </div>
  );
}
