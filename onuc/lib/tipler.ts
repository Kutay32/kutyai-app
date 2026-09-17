/** API sözleşmesindeki ortak tipler (kaynak/API.md §2). */

import type { SozlukAnahtari } from "@/lib/sozluk";

export type Rol = "yonetici" | "operator" | "izleyici" | "son_kullanici";
export type KullaniciDurumu = "aktif" | "beklemede" | "pasif";

export type Kullanici = {
  id: number;
  eposta: string;
  ad_soyad: string;
  rol: Rol;
  durum: KullaniciDurumu;
  eposta_dogrulandi: boolean;
  olusturulma: string;
  son_giris: string | null;
};

export type GirisYaniti = {
  erisim_jetonu: string;
  yenileme_jetonu: string;
  kullanici: Kullanici;
};

export type KayitYaniti = {
  kullanici: Kullanici;
  dogrulama_gerekli: boolean;
  /** SMTP tanımlı değilken dönen doğrulama bağlantısı. */
  gelistirme_baglantisi?: string;
};

export type MesajYaniti = { mesaj: string; gelistirme_baglantisi?: string };

/** `kaynak/API.md` §2 sayfalanmış liste zarfı. */
export type Sayfa<T> = { toplam: number; sayfa: number; boyut: number; kayitlar: T[] };

/**
 * Aktif organizasyondaki üyelik rolü. Yetki kararı sunucuda bu role göre
 * verilir (API.md §15); hesabın `rol` alanı yalnız varsayılan roldür.
 */
export type UyelikRolu = "sahip" | "yonetici" | "operator" | "izleyici" | "son_kullanici";

/**
 * Kapı kararında kullanılan rol: aktif organizasyonun üyelik rolü; üyelik
 * listesi alınamadıysa hesabın varsayılan rolü (sunucu varsayılan
 * organizasyona eklerken `ROL_ESLEME` ile aynı role eşler).
 */
function yetkiRolu(kullanici: Kullanici | null, uyelikRolu: UyelikRolu | null): UyelikRolu | null {
  return uyelikRolu ?? kullanici?.rol ?? null;
}

/** Aktif organizasyonda personel mi: `/dosyalar`, `/rag/*`, `/araclar` uçları. */
export function personelMi(kullanici: Kullanici | null, uyelikRolu: UyelikRolu | null): boolean {
  const rol = yetkiRolu(kullanici, uyelikRolu);
  return rol !== null && rol !== "son_kullanici";
}

/** Aktif organizasyonda görsel/ses üretimi yapabilir mi: `/medya/*` uçları. */
export function medyaYetkiliMi(kullanici: Kullanici | null, uyelikRolu: UyelikRolu | null): boolean {
  const rol = yetkiRolu(kullanici, uyelikRolu);
  return rol === "sahip" || rol === "yonetici" || rol === "operator";
}

/** Kota sınırları; `null` sınır sınırsız anlamına gelir (API.md §13). */
export type KullanimKotasi = {
  gunluk_istek: number | null;
  kullanilan_gunluk: number;
  aylik_token: number | null;
  kullanilan_aylik: number;
  gun_sifirlanma: string;
  ay_sifirlanma: string;
};

export type KullanimSerisiNoktasi = {
  /** `YYYY-MM-DD` */
  tarih: string;
  token: number;
};

/** Kişisel kullanım özeti (`GET /kullanim/benim`). */
export type KisiselKullanim = {
  gun: number;
  toplam_istek: number;
  toplam_token: number;
  girdi_token: number;
  cikti_token: number;
  ortalama_gecikme_ms: number;
  kota: KullanimKotasi | null;
  seri: KullanimSerisiNoktasi[];
};

export const ROL_ANAHTARLARI: Record<Rol, SozlukAnahtari> = {
  yonetici: "rol.yonetici",
  operator: "rol.operator",
  izleyici: "rol.izleyici",
  son_kullanici: "rol.son_kullanici",
};

export const DURUM_ANAHTARLARI: Record<KullaniciDurumu, SozlukAnahtari> = {
  aktif: "durum.aktif",
  beklemede: "durum.beklemede",
  pasif: "durum.pasif",
};
