/** `kaynak/API.md` §18 dosya istemcisi. */

import { apiFetch } from "./api";
import type { Sayfa } from "./tipler";

export const VARSAYILAN_DOSYA_SAYFA_BOYUTU = 25;
export const DOSYA_SAYFA_BOYUTLARI = [25, 50, 100] as const;

/** `GET /dosyalar` satırı (en yeni önce). */
export type DosyaOzeti = {
  id: number;
  ad: string;
  mime: string;
  boyut: number;
  /** Sunucu boş bırakabilir; biçimleyici `—` gösterir. */
  olusturulma: string | null;
};

/** `POST /dosyalar`/`GET /dosyalar/{id}` yanıtı: meta + çıkarım özeti. */
export type DosyaDetayi = DosyaOzeti & {
  sha256: string;
  metin_uzunluk: number;
  /** Maskelenmiş çıkarılmış metin; PDF çıkarımı yoksa boş kalır. */
  metin?: string;
};

export type DosyaFiltresi = {
  arama: string;
  sayfa: number;
  boyut: number;
};

export const BASLANGIC_DOSYA_FILTRESI: DosyaFiltresi = {
  arama: "",
  sayfa: 1,
  boyut: VARSAYILAN_DOSYA_SAYFA_BOYUTU,
};

/** Yalnız dolu alanlardan sorgu dizesi üretir (`arama` boşsa gönderilmez). */
export function dosyaSorgusu(filtre: DosyaFiltresi): string {
  const parametreler = new URLSearchParams();
  const arama = filtre.arama.trim();
  if (arama) parametreler.set("arama", arama);
  parametreler.set("sayfa", String(filtre.sayfa));
  parametreler.set("boyut", String(filtre.boyut));
  return parametreler.toString();
}

/**
 * `POST /dosyalar` multipart gövdesi: zorunlu `dosya` + opsiyonel `ad` alanı.
 *
 * `ad` verilmezse sunucu dosya adını kullanır.
 */
export function dosyaFormu(dosya: File, ad?: string): FormData {
  const govde = new FormData();
  govde.append("dosya", dosya);
  if (ad) govde.append("ad", ad);
  return govde;
}

/** Aktif organizasyonun dosyaları (en yeni önce). */
export async function dosyalariGetir(filtre: DosyaFiltresi): Promise<Sayfa<DosyaOzeti>> {
  return apiFetch<Sayfa<DosyaOzeti>>(`/dosyalar?${dosyaSorgusu(filtre)}`);
}

/** Dosya metası ve maskelenmiş metni; başka organizasyonun kaydı `404` verir. */
export async function dosyaDetayiGetir(dosyaId: number): Promise<DosyaDetayi> {
  return apiFetch<DosyaDetayi>(`/dosyalar/${dosyaId}`);
}

/**
 * Multipart dosya yükler; MIME ve boyut denetimini sunucu uygular
 * (`400 dosya_tur_desteklenmiyor`, `413 dosya_cok_buyuk`).
 */
export async function dosyaYukle(dosya: File, ad?: string): Promise<DosyaDetayi> {
  return apiFetch<DosyaDetayi>("/dosyalar", { method: "POST", govde: dosyaFormu(dosya, ad) });
}

/** Kaydı ve diskteki kopyayı siler. */
export async function dosyaSil(dosyaId: number): Promise<void> {
  await apiFetch<void>(`/dosyalar/${dosyaId}`, { method: "DELETE" });
}

/** Ham içeriği indirir; tarayıcıda `Content-Disposition` yerine verilen ad kullanılır. */
export async function dosyaIcerikIndir(dosya: { id: number; ad: string }): Promise<void> {
  const blob = await apiFetch<Blob>(`/dosyalar/${dosya.id}/icerik`, { ham: true });
  indirilenBlobuAc(blob, dosya.ad);
}

/** Blobu geçici bir bağlantıyla indirir; URL iş biter bitmez serbest bırakılır. */
export function indirilenBlobuAc(blob: Blob, ad: string): void {
  const adres = URL.createObjectURL(blob);
  const baglanti = document.createElement("a");
  baglanti.href = adres;
  baglanti.download = ad;
  baglanti.rel = "noopener";
  document.body.append(baglanti);
  baglanti.click();
  baglanti.remove();
  // Bazı tarayıcılar indirmeyi hemen başlatmaz; URL kısa bir gecikmeyle bırakılır.
  window.setTimeout(() => URL.revokeObjectURL(adres), 10_000);
}
