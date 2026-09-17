/** `kaynak/API.md` §20 bilgi tabanı (RAG) istemcisi. */

import { apiFetch } from "./api";
import type { SozlukAnahtari } from "./sozluk";

/** Belgenin kaynağı: satır içi metin, yüklenmiş dosya ya da bağlantı. */
export type BelgeKaynagi = "metin" | "dosya" | "url";

/** `GET /rag/belgeler` satırı. */
export type BelgeOzeti = {
  id: number;
  ad: string;
  kaynak: BelgeKaynagi;
  dosya_id: number | null;
  meta: Record<string, unknown>;
  parca_sayisi: number;
  olusturulma: string | null;
};

/** Kaynak türü etiketleri katalogdan gelir (spec §10.2); bunlar anahtar eşlemesidir. */
export const KAYNAK_ANAHTARI: Record<BelgeKaynagi, SozlukAnahtari> = {
  metin: "bilgi.kaynak.metin",
  dosya: "bilgi.kaynak.dosya",
  url: "bilgi.kaynak.url",
};

/** Aktif organizasyonun bilgi tabanı belgeleri (en yeni önce). */
export async function belgeleriGetir(): Promise<BelgeOzeti[]> {
  return apiFetch<BelgeOzeti[]>("/rag/belgeler");
}
