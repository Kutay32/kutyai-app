"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  ceviri,
  DESTEKLENEN_DILLER,
  DIL_CEREZI,
  dilGecerliMi,
  VARSAYILAN_DIL,
  type Degiskenler,
  type Dil,
  type SozlukAnahtari,
} from "@/lib/sozluk";

export type DilBaglami = {
  dil: Dil;
  diller: readonly Dil[];
  dilDegistir: (dil: Dil) => void;
  t: (anahtar: SozlukAnahtari, degiskenler?: Degiskenler) => string;
};

const Baglam = createContext<DilBaglami | null>(null);

function cerezYaz(dil: Dil): void {
  document.cookie = `${DIL_CEREZI}=${dil}; path=/; max-age=31536000; SameSite=Lax`;
}

export type DilSaglayiciOzellikleri = {
  /** Sunucunun çerezden çözdüğü dil; ilk boyama ile istemci durumunu eşitler. */
  baslangicDili?: Dil;
  children: React.ReactNode;
};

/**
 * Dil durumunu tutan sağlayıcı (spec §10.2). Dil `localStorage` + çerezde saklanır
 * ve `<html lang>` her değişimde güncellenir; sunucu bileşenleri çerezi okur.
 */
export function DilSaglayici({
  baslangicDili = VARSAYILAN_DIL,
  children,
}: DilSaglayiciOzellikleri) {
  const [dil, setDil] = useState<Dil>(baslangicDili);

  // Çerez ile localStorage çakışırsa (başka sekme/istemci) istemci tercihi kazanır.
  useEffect(() => {
    let kayitli: string | null = null;
    try {
      kayitli = window.localStorage.getItem(DIL_CEREZI);
    } catch {
      kayitli = null;
    }
    if (dilGecerliMi(kayitli) && kayitli !== baslangicDili) setDil(kayitli);
  }, [baslangicDili]);

  useEffect(() => {
    document.documentElement.lang = dil;
  }, [dil]);

  const dilDegistir = useCallback((yeni: Dil) => {
    setDil(yeni);
    cerezYaz(yeni);
    try {
      window.localStorage.setItem(DIL_CEREZI, yeni);
    } catch {
      // Depo kapalı; çerez yeterli.
    }
  }, []);

  const t = useCallback(
    (anahtar: SozlukAnahtari, degiskenler?: Degiskenler) => ceviri(anahtar, dil, degiskenler),
    [dil],
  );

  const deger = useMemo<DilBaglami>(
    () => ({ dil, diller: DESTEKLENEN_DILLER, dilDegistir, t }),
    [dil, dilDegistir, t],
  );

  return <Baglam.Provider value={deger}>{children}</Baglam.Provider>;
}

export function useDil(): DilBaglami {
  const baglam = useContext(Baglam);
  if (!baglam) {
    throw new Error("useDil yalnızca DilSaglayici içinde kullanılabilir.");
  }
  return baglam;
}
