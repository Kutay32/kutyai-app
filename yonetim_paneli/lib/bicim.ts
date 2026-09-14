/** Tarih/sayı biçimlendirme yardımcıları; yerel kod aktif dile göre seçilir. */

import { aktifDil, ceviri, type Dil } from "@/lib/sozluk";

const YEREL_KODU: Record<Dil, string> = { tr: "tr-TR", en: "en-US" };

const TARIH_SAAT = new Map<Dil, Intl.DateTimeFormat>();
const SAYI = new Map<Dil, Intl.NumberFormat>();

function tarihSaat(dil: Dil): Intl.DateTimeFormat {
  let bicimleyici = TARIH_SAAT.get(dil);
  if (!bicimleyici) {
    bicimleyici = new Intl.DateTimeFormat(YEREL_KODU[dil], {
      dateStyle: "medium",
      timeStyle: "short",
    });
    TARIH_SAAT.set(dil, bicimleyici);
  }
  return bicimleyici;
}

function sayi(dil: Dil): Intl.NumberFormat {
  let bicimleyici = SAYI.get(dil);
  if (!bicimleyici) {
    bicimleyici = new Intl.NumberFormat(YEREL_KODU[dil]);
    SAYI.set(dil, bicimleyici);
  }
  return bicimleyici;
}

/** ISO zaman damgasını yerel saatle okunur biçime çevirir. */
export function tarihSaatBicimle(deger: string | null | undefined): string {
  if (!deger) return "—";
  const tarih = new Date(deger);
  return Number.isNaN(tarih.getTime()) ? "—" : tarihSaat(aktifDil()).format(tarih);
}

/** Binlik ayraçlı tam sayı. */
export function sayiBicimle(deger: number | null | undefined): string {
  return typeof deger === "number" && Number.isFinite(deger)
    ? sayi(aktifDil()).format(deger)
    : "—";
}

/** Gecikmeyi okunur biçime çevirir (ms → sn). */
export function gecikmeBicimle(milisaniye: number | null | undefined): string {
  if (typeof milisaniye !== "number" || !Number.isFinite(milisaniye)) return "—";
  const dil = aktifDil();
  if (milisaniye >= 1000) {
    const deger = sayi(dil).format(Math.round(milisaniye / 100) / 10);
    return ceviri("bicim.saniye", dil, { deger });
  }
  const deger = sayi(dil).format(Math.round(milisaniye));
  return ceviri("bicim.milisaniye", dil, { deger });
}
