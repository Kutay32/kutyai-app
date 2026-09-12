/** Kişisel kullanım ucu, kota hesabı ve grafik ölçekleme (API.md §13). */

import { apiFetch } from "./api";
import type { KisiselKullanim } from "./tipler";

export const GUN_SECENEKLERI = [7, 30, 90] as const;
export const VARSAYILAN_GUN = 30;

/**
 * Oturum sahibinin son `gun` güne ait kişisel kullanım özetini getirir.
 *
 * `/kullanim/ozet` ve `/kullanim/zaman-serisi` personel yetkisi istediği ve
 * `onuc`'a girebilen tek rol `son_kullanici` olduğu için `onuc` yalnız bu ucu
 * çağırır (gözlem bulgusu 1 — BLOCKER).
 */
export function kisiselKullanimGetir(gun: number): Promise<KisiselKullanim> {
  return apiFetch<KisiselKullanim>(`/kullanim/benim?gun=${gun}`);
}

/** Kota kullanım oranı (%); sınır tanımsız veya sıfırsa `null` (sınırsız). */
export function kotaYuzdesi(kullanilan: number, sinir: number | null): number | null {
  if (sinir === null || sinir <= 0) return null;
  const oran = (Math.max(0, kullanilan) / sinir) * 100;
  return Math.min(100, Math.round(oran));
}

/**
 * Günlük token serisini çubuk yüksekliklerine (%) çevirir; en yüksek gün %100.
 * Sıfırdan büyük her gün en az %2 yükseklik alır ki çubuk görünür kalsın.
 */
export function seriYukseklikleri(seri: { token: number }[]): number[] {
  const enYuksek = seri.reduce((enBuyuk, nokta) => Math.max(enBuyuk, nokta.token), 0);
  if (enYuksek <= 0) return seri.map(() => 0);
  return seri.map((nokta) =>
    nokta.token > 0 ? Math.max(2, Math.round((nokta.token / enYuksek) * 100)) : 0,
  );
}
