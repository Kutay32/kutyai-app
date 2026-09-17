import { VARSAYILAN_DIL, type Dil } from "./sozluk/index";

/** Aktif dilin `Intl` yerel kodu (spec §10.2). */
const YEREL_KODLARI: Record<Dil, string> = { tr: "tr-TR", en: "en-US" };

const TARIH_SECENEKLERI: Intl.DateTimeFormatOptions = {
  day: "2-digit",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

const KISA_TARIH_SECENEKLERI: Intl.DateTimeFormatOptions = {
  day: "numeric",
  month: "short",
};

/** Biçimleyiciler dil başına bir kez kurulur (saf modül; React import edilmez). */
const tarihBicimleyicileri = {
  tr: new Intl.DateTimeFormat(YEREL_KODLARI.tr, TARIH_SECENEKLERI),
  en: new Intl.DateTimeFormat(YEREL_KODLARI.en, TARIH_SECENEKLERI),
} satisfies Record<Dil, Intl.DateTimeFormat>;

const kisaTarihBicimleyicileri = {
  tr: new Intl.DateTimeFormat(YEREL_KODLARI.tr, KISA_TARIH_SECENEKLERI),
  en: new Intl.DateTimeFormat(YEREL_KODLARI.en, KISA_TARIH_SECENEKLERI),
} satisfies Record<Dil, Intl.DateTimeFormat>;

const sayiBicimleyicileri = {
  tr: new Intl.NumberFormat(YEREL_KODLARI.tr),
  en: new Intl.NumberFormat(YEREL_KODLARI.en),
} satisfies Record<Dil, Intl.NumberFormat>;

/** ISO tarih dizesini aktif dilde okunur biçime çevirir; geçersiz/boş değerde "—" döner. */
export function tarihBicimle(deger: string | null | undefined, dil: Dil = VARSAYILAN_DIL): string {
  if (!deger) return "—";
  const tarih = new Date(deger);
  if (Number.isNaN(tarih.getTime())) return "—";
  return tarihBicimleyicileri[dil].format(tarih);
}

/** `YYYY-MM-DD` gibi tarihleri gün ay kısaltmasıyla yazar ("1 Eyl"); geçersiz değerde "—" döner. */
export function kisaTarihBicimle(
  deger: string | null | undefined,
  dil: Dil = VARSAYILAN_DIL,
): string {
  if (!deger) return "—";
  const tarih = new Date(deger);
  if (Number.isNaN(tarih.getTime())) return "—";
  return kisaTarihBicimleyicileri[dil].format(tarih);
}

/** Sayıları aktif dilin binlik ayracıyla yazar. */
export function sayiBicimle(
  deger: number | null | undefined,
  dil: Dil = VARSAYILAN_DIL,
): string {
  if (deger === null || deger === undefined) return "—";
  return sayiBicimleyicileri[dil].format(deger);
}

const BOYUT_BIRIMLERI = ["B", "KB", "MB", "GB", "TB"] as const;

/** Boyut sayıları en çok bir ondalıkla yazılır (ör. `1,2`). */
const boyutBicimleyicileri = {
  tr: new Intl.NumberFormat(YEREL_KODLARI.tr, { maximumFractionDigits: 1 }),
  en: new Intl.NumberFormat(YEREL_KODLARI.en, { maximumFractionDigits: 1 }),
} satisfies Record<Dil, Intl.NumberFormat>;

/** Baytı okunur boyuta çevirir (ör. `1,2 MB`); geçersiz değerde "—" döner. */
export function boyutBicimle(
  bayt: number | null | undefined,
  dil: Dil = VARSAYILAN_DIL,
): string {
  if (typeof bayt !== "number" || !Number.isFinite(bayt)) return "—";
  let deger = Math.max(0, bayt);
  let indeks = 0;
  while (deger >= 1024 && indeks < BOYUT_BIRIMLERI.length - 1) {
    deger /= 1024;
    indeks += 1;
  }
  return `${boyutBicimleyicileri[dil].format(deger)} ${BOYUT_BIRIMLERI[indeks]}`;
}

/** Arama karşılaştırması için metni aktif dilin küçük harf kurallarına çevirir. */
export function kucukHarfeCevir(metin: string, dil: Dil = VARSAYILAN_DIL): string {
  return metin.toLocaleLowerCase(YEREL_KODLARI[dil]);
}
