"use client";

import { useEffect, useState } from "react";

import { Yukleniyor } from "@/components/ui/yukleniyor";
import { useDil } from "@/lib/dil";
import { uretilenDosyaBlobu, type UretilenDosya } from "@/lib/medya";

type AdresDurumu = { adres: string | null; hata: boolean };

/**
 * Üretilen dosyanın içeriğini nesne URL'ine çevirir.
 *
 * İndirme bağlantısı jetonlu istek gerektirdiği için `<img>`/`<audio>` doğrudan
 * uca bağlanamaz; içerik bir kez çekilir, URL bileşen kapanınca bırakılır.
 */
function useDosyaAdresi(dosyaId: number): AdresDurumu {
  const [durum, setDurum] = useState<AdresDurumu>({ adres: null, hata: false });

  useEffect(() => {
    let iptal = false;
    let adres: string | null = null;
    setDurum({ adres: null, hata: false });
    uretilenDosyaBlobu(dosyaId)
      .then((blob) => {
        if (iptal) return;
        adres = URL.createObjectURL(blob);
        setDurum({ adres, hata: false });
      })
      .catch(() => {
        if (!iptal) setDurum({ adres: null, hata: true });
      });
    return () => {
      iptal = true;
      if (adres) URL.revokeObjectURL(adres);
    };
  }, [dosyaId]);

  return durum;
}

/** Üretilen görselin önizlemesi; yüklenene kadar iskelet gösterilir. */
export function GorselOnizleme({ dosya }: { dosya: UretilenDosya }) {
  const { t } = useDil();
  const { adres, hata } = useDosyaAdresi(dosya.dosya_id);

  if (hata) return <p className="text-[13px] text-neutral-500">{t("medya.onizleme.hata")}</p>;
  if (!adres) return <div aria-hidden className="h-40 w-40 animate-pulse rounded-md bg-neutral-100" />;
  // Görsel jetonsuz bir nesne URL'inden gelir; `next/image` optimizasyonu uygulanamaz.
  return (
    <img
      src={adres}
      alt={t("medya.onizleme", { ad: dosya.ad })}
      className="max-h-64 max-w-full rounded-md border border-neutral-200 object-contain"
    />
  );
}

/** Üretilen sesin oynatıcısı; yüklenene kadar dönen gösterge basılır. */
export function SesOynatici({ dosya }: { dosya: UretilenDosya }) {
  const { t } = useDil();
  const { adres, hata } = useDosyaAdresi(dosya.dosya_id);

  if (hata) return <p className="text-[13px] text-neutral-500">{t("medya.onizleme.hata")}</p>;
  if (!adres) return <Yukleniyor boyut="kucuk" />;
  return (
    <audio
      controls
      src={adres}
      aria-label={t("medya.ses.oynatici", { ad: dosya.ad })}
      className="h-10 w-full max-w-md"
    />
  );
}
