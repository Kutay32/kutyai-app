"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { UygulamaKabugu } from "@/components/uygulama-kabugu";
import { Yukleniyor } from "@/components/ui/yukleniyor";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { oturumAl } from "@/lib/oturum";
import type { Kullanici } from "@/lib/tipler";

export type KorumaliOzellikleri = {
  children: React.ReactNode;
  tamYukseklik?: boolean;
};

/** Oturum denetimi yapıp uygulama kabuğunu basan korumalı rota sarmalayıcısı. */
export function Korumali({ children, tamYukseklik = false }: KorumaliOzellikleri) {
  const yonlendirici = useRouter();
  const [kullanici, setKullanici] = useState<Kullanici | null>(null);
  const [hazir, setHazir] = useState(false);

  useEffect(() => {
    let iptal = false;
    if (!oturumAl()) {
      yonlendirici.replace("/giris");
      return;
    }
    apiFetch<Kullanici>("/kimlik/ben")
      .then((yanit) => {
        if (iptal) return;
        setKullanici(yanit);
        setHazir(true);
      })
      .catch((hata: unknown) => {
        if (iptal) return;
        // 401/403: apiFetch oturumu kapatıp /giris'e yönlendirdi.
        if (hata instanceof ApiHatasi && (hata.durum === 401 || hata.durum === 403)) {
          yonlendirici.replace("/giris");
          return;
        }
        // Uç henüz yoksa/geçici hata varsa kabuk yine açılır, veri istekleri hatayı gösterir.
        setHazir(true);
      });
    return () => {
      iptal = true;
    };
  }, [yonlendirici]);

  if (!hazir) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-white">
        <Yukleniyor etiket="Oturum denetleniyor" />
      </div>
    );
  }

  return (
    <UygulamaKabugu kullanici={kullanici} tamYukseklik={tamYukseklik}>
      {children}
    </UygulamaKabugu>
  );
}
