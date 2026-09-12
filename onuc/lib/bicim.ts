const tarihBicimleyici = new Intl.DateTimeFormat("tr-TR", {
  day: "2-digit",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** ISO tarih dizesini Türkçe okunur biçime çevirir; geçersiz/boş değerde "—" döner. */
export function tarihBicimle(deger: string | null | undefined): string {
  if (!deger) return "—";
  const tarih = new Date(deger);
  if (Number.isNaN(tarih.getTime())) return "—";
  return tarihBicimleyici.format(tarih);
}

const kisaTarihBicimleyici = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "short",
});

/** `YYYY-MM-DD` gibi tarihleri gün ay kısaltmasıyla yazar ("1 Eyl"); geçersiz değerde "—" döner. */
export function kisaTarihBicimle(deger: string | null | undefined): string {
  if (!deger) return "—";
  const tarih = new Date(deger);
  if (Number.isNaN(tarih.getTime())) return "—";
  return kisaTarihBicimleyici.format(tarih);
}

/** Sayıları Türkçe binlik ayracıyla yazar. */
export function sayiBicimle(deger: number | null | undefined): string {
  if (deger === null || deger === undefined) return "—";
  return new Intl.NumberFormat("tr-TR").format(deger);
}
