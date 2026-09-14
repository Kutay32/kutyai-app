/** `kaynak/API.md` §12 konuşma kayıtları istemcisi. */

import { dosyaIndir, istek } from "@/lib/api";
import type { SozlukAnahtari } from "@/lib/sozluk";
import type { LogKonusmasi, Sayfa } from "@/lib/tipler";

export const VARSAYILAN_LOG_SAYFA_BOYUTU = 25;
export const LOG_SAYFA_BOYUTLARI = [25, 50, 100] as const;

export const DISA_AKTARIM_BICIMLERI = ["json", "md", "csv"] as const;
export type DisaAktarimBicimi = (typeof DISA_AKTARIM_BICIMLERI)[number];

export const DISA_AKTARIM_ETIKETI: Record<DisaAktarimBicimi, string> = {
  json: "JSON",
  md: "MD",
  csv: "CSV",
};

export type LogFiltresi = {
  /** Boş bırakılırsa sunucu tüm kullanıcıları getirir. */
  kullanici_id: number | null;
  bdm_id: number | null;
  /** `YYYY-AA-GG` (yerel gün); sunucuya UTC gün sınırı olarak gider. */
  baslangic: string;
  bitis: string;
  arama: string;
  sayfa: number;
  boyut: number;
};

export const BASLANGIC_LOG_FILTRESI: LogFiltresi = {
  kullanici_id: null,
  bdm_id: null,
  baslangic: "",
  bitis: "",
  arama: "",
  sayfa: 1,
  boyut: VARSAYILAN_LOG_SAYFA_BOYUTU,
};

export type LogMesajRolu = "kullanici" | "asistan" | "sistem" | "arac";

/** `GET /loglar/konusmalar/{id}` mesaj kaydı (içerik maskelenmiş olarak saklanır). */
export type LogMesaji = {
  id: number;
  rol: LogMesajRolu;
  icerik: string;
  token_sayisi: number;
  gecikme_ms: number;
  model: string;
  hata: string | null;
  olusturulma: string;
};

export type LogDetayi = {
  id: number;
  baslik: string;
  bdm_id: number | null;
  bdm_ad: string | null;
  kullanici_id: number | null;
  kullanici_eposta: string | null;
  api_anahtari_id: number | null;
  sistem_istemi: string;
  token_girdi: number;
  token_cikti: number;
  olusturulma: string;
  guncellenme: string;
  mesajlar: LogMesaji[];
};

/** Mesaj rolü etiketleri katalogdan gelir (spec §10.2); bunlar anahtar eşlemesidir. */
export const MESAJ_ROL_ANAHTARI: Record<LogMesajRolu, SozlukAnahtari> = {
  kullanici: "kayit.rol.kullanici",
  asistan: "kayit.rol.asistan",
  sistem: "kayit.rol.sistem",
  arac: "kayit.rol.arac",
};

/** Yerel günün başlangıç/son anını API'nin beklediği UTC ISO damgasına çevirir. */
export function gunSiniriIso(gun: string, son: boolean): string | null {
  if (!gun) return null;
  const tarih = new Date(`${gun}T${son ? "23:59:59.999" : "00:00:00.000"}`);
  return Number.isNaN(tarih.getTime()) ? null : tarih.toISOString();
}

/** Dolu filtre alanlarından sorgu dizesi üretir; boş alanlar hiç gönderilmez. */
export function logSorgusu(filtre: LogFiltresi): string {
  const parametreler = new URLSearchParams();
  if (filtre.kullanici_id !== null) {
    parametreler.set("kullanici_id", String(filtre.kullanici_id));
  }
  if (filtre.bdm_id !== null) parametreler.set("bdm_id", String(filtre.bdm_id));

  const baslangic = gunSiniriIso(filtre.baslangic, false);
  const bitis = gunSiniriIso(filtre.bitis, true);
  if (baslangic) parametreler.set("baslangic", baslangic);
  if (bitis) parametreler.set("bitis", bitis);

  const arama = filtre.arama.trim();
  if (arama) parametreler.set("arama", arama);

  parametreler.set("sayfa", String(filtre.sayfa));
  parametreler.set("boyut", String(filtre.boyut));
  return parametreler.toString();
}

/** Sayfalanmış konuşma kayıtları. */
export async function loglariGetir(filtre: LogFiltresi): Promise<Sayfa<LogKonusmasi>> {
  return istek<Sayfa<LogKonusmasi>>(`/loglar/konusmalar?${logSorgusu(filtre)}`);
}

/** Tek konuşmanın mesajlarıyla birlikte detayı. */
export async function logDetayiGetir(konusmaId: number): Promise<LogDetayi> {
  return istek<LogDetayi>(`/loglar/konusmalar/${konusmaId}`);
}

/** Konuşmayı json/md/csv olarak indirir (sunucu `Content-Disposition` ile ad verir). */
export async function logDisaAktar(
  konusmaId: number,
  bicim: DisaAktarimBicimi,
): Promise<void> {
  await dosyaIndir(
    `/loglar/konusmalar/${konusmaId}/disa-aktar?bicim=${bicim}`,
    `konusma-${konusmaId}.${bicim}`,
  );
}

/** Konuşmayı kalıcı olarak siler (yönetici/operatör; izleyici `403` alır). */
export async function logSil(konusmaId: number): Promise<void> {
  await istek<void>(`/loglar/konusmalar/${konusmaId}`, { yontem: "DELETE" });
}

/** Saklama süresini aşan kayıtları siler; `gun` verilmezse `saklama_gun` kullanılır. */
export async function loglariTemizle(gun: number | null): Promise<{ silinen: number }> {
  return istek<{ silinen: number }>("/loglar/temizle", {
    yontem: "POST",
    govde: gun === null ? {} : { gun },
  });
}
