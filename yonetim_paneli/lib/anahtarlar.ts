/** `kaynak/API.md` §7 API anahtarları istemcisi (yönetici/operatör). */

import { istek } from "@/lib/api";

export type AnahtarDurumu = "aktif" | "iptal";

/** `GET /api-anahtarlari` kaydı — tam anahtar hiçbir okumada dönmez. */
export type ApiAnahtari = {
  id: number;
  ad: string;
  onek: string;
  son_dort: string;
  durum: AnahtarDurumu;
  izinli_modeller: string[];
  gunluk_istek_siniri: number | null;
  olusturulma: string | null;
  son_kullanim: string | null;
};

/** `POST /api-anahtarlari` yanıtı: `tam_anahtar` yalnızca burada bulunur. */
export type YeniApiAnahtari = ApiAnahtari & { tam_anahtar: string };

export type AnahtarIstegi = {
  ad: string;
  /** Boş liste "tüm modeller" demektir. */
  izinli_modeller: string[];
};

export const ANAHTAR_DURUMU_ETIKETI: Record<AnahtarDurumu, string> = {
  aktif: "Aktif",
  iptal: "İptal edildi",
};

export function anahtarlariGetir(): Promise<ApiAnahtari[]> {
  return istek<ApiAnahtari[]>("/api-anahtarlari");
}

export function anahtarOlustur(girdi: AnahtarIstegi): Promise<YeniApiAnahtari> {
  return istek<YeniApiAnahtari>("/api-anahtarlari", { yontem: "POST", govde: girdi });
}

export function anahtarIptal(anahtarId: number): Promise<{ durum: AnahtarDurumu }> {
  return istek<{ durum: AnahtarDurumu }>(`/api-anahtarlari/${anahtarId}/iptal`, {
    yontem: "POST",
  });
}
