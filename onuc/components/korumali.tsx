"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { UygulamaKabugu } from "@/components/uygulama-kabugu";
import { Yukleniyor } from "@/components/ui/yukleniyor";
import { ApiHatasi, apiFetch } from "@/lib/api";
import { useDil } from "@/lib/dil";
import { aktifUyelikRolu, organizasyonlariGetir } from "@/lib/organizasyonlar";
import { jetonOrganizasyonId, oturumAl } from "@/lib/oturum";
import type { Kullanici, UyelikRolu } from "@/lib/tipler";

/**
 * `/kimlik/ben` yanıtı ve aktif organizasyondaki üyelik rolü alt ekranlara
 * bağlamla taşınır; sayfalar yetki kararını ikinci bir istek atmadan verir.
 * Kabuk hazır olmadan çocuklar basılmadığı için değer ya dolu ya `null`dır.
 */
const KullaniciBaglami = createContext<Kullanici | null>(null);
const UyelikBaglami = createContext<UyelikRolu | null>(null);

export function useKullanici(): Kullanici | null {
  return useContext(KullaniciBaglami);
}

/**
 * Aktif organizasyondaki üyelik rolü (yetenek kapıları bunu kullanır).
 * Üyelik listesi alınamadıysa `null` döner; kapılar hesabın varsayılan rolüne düşer.
 */
export function useUyelikRolu(): UyelikRolu | null {
  return useContext(UyelikBaglami);
}

export type KorumaliOzellikleri = {
  children: React.ReactNode;
  tamYukseklik?: boolean;
};

/** Oturum denetimi yapıp uygulama kabuğunu basan korumalı rota sarmalayıcısı. */
export function Korumali({ children, tamYukseklik = false }: KorumaliOzellikleri) {
  const yonlendirici = useRouter();
  const { t } = useDil();
  const [kullanici, setKullanici] = useState<Kullanici | null>(null);
  const [uyelikRolu, setUyelikRolu] = useState<UyelikRolu | null>(null);
  const [hazir, setHazir] = useState(false);

  useEffect(() => {
    let iptal = false;
    if (!oturumAl()) {
      yonlendirici.replace("/giris");
      return;
    }
    // Üyelik rolü `/kimlik/ben` ile paralel çözülür; liste alınamazsa (404/ağ)
    // yetenek kapıları hesabın varsayılan rolüne düşer, kabuk yine açılır.
    const uyelikSozu = organizasyonlariGetir()
      .then((liste) => aktifUyelikRolu(liste, jetonOrganizasyonId()))
      .catch(() => null);

    void (async () => {
      try {
        const yanit = await apiFetch<Kullanici>("/kimlik/ben");
        if (iptal) return;
        setKullanici(yanit);
        setUyelikRolu(await uyelikSozu);
        setHazir(true);
      } catch (hata: unknown) {
        if (iptal) return;
        // 401/403: apiFetch oturumu kapatıp /giris'e yönlendirdi.
        if (hata instanceof ApiHatasi && (hata.durum === 401 || hata.durum === 403)) {
          yonlendirici.replace("/giris");
          return;
        }
        // Uç henüz yoksa/geçici hata varsa kabuk yine açılır, veri istekleri hatayı gösterir.
        setUyelikRolu(await uyelikSozu);
        setHazir(true);
      }
    })();
    return () => {
      iptal = true;
    };
  }, [yonlendirici]);

  if (!hazir) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-white">
        <Yukleniyor etiket={t("kabuk.oturum.denetleniyor")} />
      </div>
    );
  }

  return (
    <KullaniciBaglami.Provider value={kullanici}>
      <UyelikBaglami.Provider value={uyelikRolu}>
        <UygulamaKabugu
          kullanici={kullanici}
          uyelikRolu={uyelikRolu}
          tamYukseklik={tamYukseklik}
        >
          {children}
        </UygulamaKabugu>
      </UyelikBaglami.Provider>
    </KullaniciBaglami.Provider>
  );
}
