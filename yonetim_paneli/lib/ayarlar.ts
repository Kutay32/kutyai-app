/** `kaynak/API.md` §14 ayar uçları istemcisi (yalnız yönetici). */

import { istek } from "@/lib/api";

/**
 * `GET /ayarlar` yanıtı. `smtp_port`, `smtp_kullanici` ve `smtp_tls` sunucu
 * tarafından geri döndürülmez; yalnızca yazılabilir alanlardır. `smtp_sifre`
 * hiçbir yanıtta yer almaz, varlığı `smtp_tanimli` ile temsil edilir.
 */
export type Ayarlar = {
  marka_adi: string;
  kurulum_tamam: boolean;
  saklama_gun: number;
  maskeleme_aktif: boolean;
  kayit_acik: boolean;
  smtp_host: string;
  smtp_gonderen: string;
  smtp_tanimli: boolean;
  bakim_modu: boolean;
};

/** Yazma gövdesi: `null` geçilen alan hiç gönderilmez ve değişmez. */
export type AyarGuncellemesi = {
  marka_adi?: string;
  saklama_gun?: number;
  maskeleme_aktif?: boolean;
  kayit_acik?: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_kullanici?: string;
  smtp_sifre?: string;
  smtp_gonderen?: string;
  smtp_tls?: boolean;
  bakim_modu?: boolean;
};

export const VARSAYILAN_SAKLAMA_GUNU = 90;
export const TEHLIKELI_GUN_SECENEKLERI = [7, 30, 90, 180] as const;

export function ayarlariGetir(): Promise<Ayarlar> {
  return istek<Ayarlar>("/ayarlar");
}

/** Yalnızca gönderilen alanları günceller; güncel ayarları döndürür. */
export function ayarlariGuncelle(girdi: AyarGuncellemesi): Promise<Ayarlar> {
  return istek<Ayarlar>("/ayarlar", { yontem: "PUT", govde: girdi });
}
