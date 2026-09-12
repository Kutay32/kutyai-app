/** `kaynak/API.md` §2 ve §3-§14 ile birebir eşleşen yanıt tipleri. */

export type Rol = "yonetici" | "operator" | "izleyici" | "son_kullanici";
export type KullaniciDurumu = "aktif" | "beklemede" | "pasif";
export type Saglayici =
  | "openai"
  | "azure"
  | "openrouter"
  | "ollama"
  | "vllm"
  | "tgi"
  | "ozel";
export type BdmDurumu = "taslak" | "hazir" | "calisiyor" | "durdu" | "hata";

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

export type Sayfa<T> = {
  toplam: number;
  sayfa: number;
  boyut: number;
  kayitlar: T[];
};

export type BdmYetenekler = {
  akis: boolean;
  gorsel: boolean;
  arac: boolean;
};

export type BdmKonteyner = {
  image?: string;
  gpu?: boolean;
  port?: number;
  bellek_gb?: number;
};

export type Bdm = {
  id: number;
  slug: string;
  gorunen_ad: string;
  aciklama: string;
  saglayici: Saglayici;
  temel_url: string;
  upstream_model: string;
  api_anahtari_maskeli: string;
  baglam_penceresi: number;
  maks_cikti: number;
  sicaklik_varsayilan: number;
  sistem_istemi: string;
  yetenekler: BdmYetenekler;
  durum: BdmDurumu;
  yerel_mi: boolean;
  konteyner: BdmKonteyner | null;
  olusturulma: string;
  guncellenme: string;
};

export type BdmOzet = Pick<
  Bdm,
  | "id"
  | "slug"
  | "gorunen_ad"
  | "aciklama"
  | "saglayici"
  | "baglam_penceresi"
  | "yetenekler"
  | "durum"
>;

/** `bdm_listesi/saglayicilar.py` → `saglayici_listesi()` çıktısı. */
export type SaglayiciBilgisi = {
  ad: Saglayici;
  gorunen_ad: string;
  yerel: boolean;
  gpu_gerekir: boolean;
  akis_destegi: boolean;
  api_anahtari_gerekir: boolean;
  varsayilan_temel_url: string;
  varsayilan_port: number | null;
  konteyner_image: string | null;
  aciklama: string;
};

export type SaglikYaniti = {
  durum: string;
  surum: string;
  ortam: string;
  zaman: string;
};

export type KurulumDurumu = {
  kurulum_tamam: boolean;
  marka_adi: string;
  surum: string;
};

export type KullanimOzeti = {
  toplam_istek: number;
  toplam_token: number;
  basarili: number;
  hatali: number;
  kota_asimi: number;
  ortalama_gecikme_ms: number;
};

export type SurucuDurumu = {
  surucu: string;
  docker: boolean;
  gpu: boolean;
  gpu_listesi: string[];
  image_onbellek: string[];
  mesaj: string;
};

/** `GET /loglar/konusmalar` kayıtları (API.md §12). */
export type LogKonusmasi = {
  id: number;
  baslik: string;
  kullanici_eposta: string | null;
  bdm_ad: string;
  mesaj_sayisi: number;
  token_girdi: number;
  token_cikti: number;
  olusturulma: string;
};

export type OturumYaniti = {
  erisim_jetonu: string;
  yenileme_jetonu: string;
  kullanici: Kullanici;
};

export type KurulumYaniti = {
  yonetici: Kullanici;
  bdm: Bdm;
  dogrulama: { basarili: boolean; mesaj: string } | null;
  kurulum_tamam: boolean;
};

export type KurulumIstegi = {
  marka_adi: string;
  yonetici: { eposta: string; ad_soyad: string; parola: string };
  bdm: {
    gorunen_ad: string;
    saglayici: Saglayici;
    temel_url: string;
    upstream_model: string;
    api_anahtari: string;
    yerel_mi: boolean;
    sistem_istemi: string;
  };
  dogrula: boolean;
};
