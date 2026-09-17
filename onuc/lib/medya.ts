/** `kaynak/API.md` §21 görsel ve ses üretimi istemcisi. */

import { apiFetch } from "./api";
import { dosyaDetayiGetir, indirilenBlobuAc } from "./dosyalar";

/** `POST /medya/gorsel` gövdesi. */
export type GorselIstegi = {
  bdm_id: number;
  istem: string;
  boyut?: string;
  adet?: number;
};

/** Üretilen medyanın dosya tablosundaki karşılığı. */
export type UretilenDosya = {
  dosya_id: number;
  ad: string;
  mime: string;
  boyut: number;
};

/** `POST /medya/ses` gövdesi. */
export type SesIstegi = {
  bdm_id: number;
  metin: string;
  ses?: string;
  bicim?: string;
};

/** Sunucudaki varsayılanlar (`arkauc/app/servisler/medya.py`). */
export const VARSAYILAN_GORSEL_BOYUTU = "1024x1024";
export const VARSAYILAN_SES = "alloy";
export const VARSAYILAN_BICIM = "mp3";

export const GORSEL_BOYUTLARI = ["1024x1024", "1792x1024", "1024x1792", "512x512"] as const;

/** OpenAI uyumlu ses adları; sunucu serbest metin kabul eder (en çok 40 karakter). */
export const SES_ADLARI = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] as const;

/** Sunucunun kabul ettiği biçimler ve MIME karşılıkları (API.md §21). */
export const SES_BICIMLERI = ["mp3", "opus", "aac", "flac", "wav", "pcm"] as const;

/**
 * Görsel üretir; sonuçlar `dosya` tablosuna yazılır.
 * Model görsel üretimini desteklemiyorsa `400 medya_desteklenmiyor` döner.
 */
export async function gorselUret(istek: GorselIstegi): Promise<UretilenDosya[]> {
  return apiFetch<UretilenDosya[]>("/medya/gorsel", { method: "POST", govde: istek });
}

/**
 * Metni sese çevirir; sonuç `dosya` tablosuna yazılır ve `dosya_id` döner.
 * Model ses üretimini desteklemiyorsa `400 medya_desteklenmiyor` döner.
 */
export async function sesUret(istek: SesIstegi): Promise<{ dosya_id: number }> {
  return apiFetch<{ dosya_id: number }>("/medya/ses", { method: "POST", govde: istek });
}

/**
 * Üretilen sesi dosya metasıyla birlikte döndürür: uç yalnız `dosya_id` verir,
 * oynatıcı/indirme için ad ve tür `GET /dosyalar/{id}`ten tamamlanır.
 */
export async function sesDosyasiUret(istek: SesIstegi): Promise<UretilenDosya> {
  const { dosya_id } = await sesUret(istek);
  const detay = await dosyaDetayiGetir(dosya_id);
  return { dosya_id: detay.id, ad: detay.ad, mime: detay.mime, boyut: detay.boyut };
}

/**
 * Üretilen dosyanın ham içeriği (önizleme ve oynatıcı için geçici bağlantıya sarılır).
 * Üretilenler `dosya` tablosuna yazıldığı için içerik `/dosyalar/{id}/icerik`ten okunur.
 */
export function uretilenDosyaBlobu(dosyaId: number): Promise<Blob> {
  return apiFetch<Blob>(`/dosyalar/${dosyaId}/icerik`, { ham: true });
}

/** Üretilen dosyayı kendi adıyla indirir. */
export async function uretilenDosyayiIndir(dosya: { dosya_id: number; ad: string }): Promise<void> {
  indirilenBlobuAc(await uretilenDosyaBlobu(dosya.dosya_id), dosya.ad);
}
