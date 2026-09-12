"use client";

import { useEffect, useState } from "react";

import { hataMesaji } from "@/lib/api";

export type UzakVeri<T> = {
  veri: T | null;
  yukleniyor: boolean;
  hata: string | null;
  yenile: () => void;
};

/**
 * Uzak veriyi bir kez yükler; yükleme/hata/veri durumunu ve yeniden denemeyi yönetir.
 * `anahtarlar` yalnız ilkel değerler içermelidir (ör. `[konusmaId]`).
 */
export function useUzakVeri<T>(
  yukleyici: () => Promise<T>,
  anahtarlar: readonly unknown[] = [],
): UzakVeri<T> {
  const [veri, setVeri] = useState<T | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);
  const [deneme, setDeneme] = useState(0);

  useEffect(() => {
    let iptal = false;
    setYukleniyor(true);
    setHata(null);

    yukleyici()
      .then((sonuc) => {
        if (!iptal) setVeri(sonuc);
      })
      .catch((sebep: unknown) => {
        if (!iptal) setHata(hataMesaji(sebep));
      })
      .finally(() => {
        if (!iptal) setYukleniyor(false);
      });

    return () => {
      iptal = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deneme, ...anahtarlar]);

  return { veri, yukleniyor, hata, yenile: () => setDeneme((onceki) => onceki + 1) };
}
