/** Türkçe tarih/sayı biçimlendirme yardımcıları. */

const TARIH_SAAT = new Intl.DateTimeFormat("tr-TR", {
  dateStyle: "medium",
  timeStyle: "short",
});

const SAYI = new Intl.NumberFormat("tr-TR");

/** ISO zaman damgasını yerel saatle okunur biçime çevirir. */
export function tarihSaatBicimle(deger: string | null | undefined): string {
  if (!deger) return "—";
  const tarih = new Date(deger);
  return Number.isNaN(tarih.getTime()) ? "—" : TARIH_SAAT.format(tarih);
}

/** Binlik ayraçlı tam sayı. */
export function sayiBicimle(deger: number | null | undefined): string {
  return typeof deger === "number" && Number.isFinite(deger) ? SAYI.format(deger) : "—";
}

/** Gecikmeyi okunur biçime çevirir (ms → sn). */
export function gecikmeBicimle(milisaniye: number | null | undefined): string {
  if (typeof milisaniye !== "number" || !Number.isFinite(milisaniye)) return "—";
  return milisaniye >= 1000
    ? `${SAYI.format(Math.round(milisaniye / 100) / 10)} sn`
    : `${SAYI.format(Math.round(milisaniye))} ms`;
}
