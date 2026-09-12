/** API sözleşmesindeki ortak tipler (kaynak/API.md §2). */

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

export const ROL_ETIKETLERI: Record<Rol, string> = {
  yonetici: "Yönetici",
  operator: "Operatör",
  izleyici: "İzleyici",
  son_kullanici: "Son kullanıcı",
};

export const DURUM_ETIKETLERI: Record<KullaniciDurumu, string> = {
  aktif: "Aktif",
  beklemede: "Beklemede",
  pasif: "Pasif",
};
