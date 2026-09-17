/** `kaynak/API.md` §20 bilgi tabanı (RAG) istemcisi. */

import { istek } from "@/lib/api";
import type { SozlukAnahtari } from "@/lib/sozluk";

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

export type BelgeParcasi = {
  sira: number;
  icerik: string;
  token_sayisi: number;
};

/** `GET /rag/belgeler/{id}`: belge + parçaları. */
export type BelgeDetayi = BelgeOzeti & { parcalar: BelgeParcasi[] };

/** `POST /rag/ara` sonuç satırı; `icerik` eşleşen parçanın metnidir. */
export type AramaSonucu = {
  belge_id: number;
  belge_ad: string;
  sira: number;
  icerik: string;
  skor: number;
};

/** `ayrinti.yol` seçilen arama yolunu bildirir (`python` ya da `pgvector`). */
export type AramaYaniti = {
  sonuclar: AramaSonucu[];
  ayrinti: { yol: string; ust_k: number };
};

/** `POST /rag/belgeler` gövdesi: `metin` ya da `dosya_id` verilmelidir. */
export type BelgeIstegi = {
  ad: string;
  bdm_id: number;
  metin?: string;
  dosya_id?: number;
  meta?: Record<string, unknown>;
};

/** `POST /rag/ara` gövdesi (`ust_k` sunucuda 1..50 ile sınırlıdır). */
export type AramaIstegi = {
  sorgu: string;
  bdm_id?: number;
  ust_k?: number;
  belge_idleri?: number[];
};

/** Sunucudaki `ayarlar.rag_ust_k` varsayılanı (spec §5). */
export const VARSAYILAN_UST_K = 4;
export const EN_BUYUK_UST_K = 50;

/** Kaynak türü etiketleri katalogdan gelir (spec §10.2); bunlar anahtar eşlemesidir. */
export const KAYNAK_ANAHTARI: Record<BelgeKaynagi, SozlukAnahtari> = {
  metin: "bilgi.kaynak.metin",
  dosya: "bilgi.kaynak.dosya",
  url: "bilgi.kaynak.url",
};

/** Aktif organizasyonun bilgi tabanı belgeleri (en yeni önce). */
export async function belgeleriGetir(): Promise<BelgeOzeti[]> {
  return istek<BelgeOzeti[]>("/rag/belgeler");
}

/** Belgeyi parçalarıyla birlikte getirir (başka organizasyonun kaydı `404`). */
export async function belgeDetayiGetir(belgeId: number): Promise<BelgeDetayi> {
  return istek<BelgeDetayi>(`/rag/belgeler/${belgeId}`);
}

/** Belgeyi parçalar, gömer ve yazar (yazma: yönetici/operatör). */
export async function belgeEkle(girdi: BelgeIstegi): Promise<BelgeOzeti> {
  return istek<BelgeOzeti>("/rag/belgeler", { yontem: "POST", govde: girdi });
}

/** Belgeyi ve parçalarını siler. */
export async function belgeSil(belgeId: number): Promise<void> {
  await istek<void>(`/rag/belgeler/${belgeId}`, { yontem: "DELETE" });
}

/**
 * Belgenin parçalarını güncel gömme modeliyle tazeler.
 * `bdm_id` verilmezse sunucu org'un ilk hazır modelini kullanır.
 */
export async function belgeYenidenGom(belgeId: number, bdmId?: number): Promise<BelgeOzeti> {
  return istek<BelgeOzeti>(`/rag/belgeler/${belgeId}/yeniden-gom`, {
    yontem: "POST",
    govde: bdmId === undefined ? {} : { bdm_id: bdmId },
  });
}

/** Sorguya en benzer parçaları (`sonuclar`) ve seçilen arama yolunu döndürür. */
export async function ragAra(girdi: AramaIstegi): Promise<AramaYaniti> {
  return istek<AramaYaniti>("/rag/ara", { yontem: "POST", govde: girdi });
}
