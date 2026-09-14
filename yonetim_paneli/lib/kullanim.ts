/** `kaynak/API.md` §13 kullanım uçları istemcisi. */

import { istek } from "@/lib/api";
import { aktifDil, type SozlukAnahtari } from "@/lib/sozluk";
import type { KullanimOzeti } from "@/lib/tipler";

export const GUN_SECENEKLERI = [7, 30, 90] as const;
export type GunSecenegi = (typeof GUN_SECENEKLERI)[number];

export const KIRILIMLAR = ["bdm", "kullanici"] as const;
export type Kirilim = (typeof KIRILIMLAR)[number];

/** Kırılım etiketleri katalogdan gelir (spec §10.2); bu yalnız anahtar eşlemesidir. */
export const KIRILIM_ANAHTARI: Record<Kirilim, SozlukAnahtari> = {
  bdm: "kullanim.kirilim.bdm",
  kullanici: "kullanim.kirilim.kullanici",
};

/** `GET /kullanim/zaman-serisi` kaydı: kırılım etiketi başına toplam. */
export type ZamanSerisiKaydi = {
  etiket: string;
  istek: number;
  token: number;
};

export const VARSAYILAN_KIRILIM_BOYUTU = 12;

export async function kullanimOzetiGetir(gun: number): Promise<KullanimOzeti> {
  return istek<KullanimOzeti>(`/kullanim/ozet?gun=${gun}`);
}

export async function kullanimZamanSerisiGetir(
  gun: number,
  kirilim: Kirilim,
): Promise<ZamanSerisiKaydi[]> {
  const yanit = await istek<{ seri: ZamanSerisiKaydi[] }>(
    `/kullanim/zaman-serisi?gun=${gun}&kirilim=${kirilim}`,
  );
  return yanit.seri;
}

/** Seriyi ölçüye göre azalan sıralar; grafik ve tablo aynı sırayı paylaşır. */
export function seriyiSirala(
  seri: ZamanSerisiKaydi[],
  olcu: keyof Pick<ZamanSerisiKaydi, "istek" | "token">,
): ZamanSerisiKaydi[] {
  return [...seri].sort((a, b) => b[olcu] - a[olcu] || a.etiket.localeCompare(b.etiket, aktifDil()));
}
