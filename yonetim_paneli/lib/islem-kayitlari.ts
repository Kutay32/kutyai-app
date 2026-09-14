/** `kaynak/API.md` §12 denetim izi istemcisi (personel; en yeni önce). */

import { istek } from "@/lib/api";
import { gunSiniriIso } from "@/lib/loglar";
import { aktifDil, ceviri, type SozlukAnahtari } from "@/lib/sozluk";
import type { Sayfa } from "@/lib/tipler";

export const VARSAYILAN_ISLEM_SAYFA_BOYUTU = 25;
export const ISLEM_SAYFA_BOYUTLARI = [25, 50, 100] as const;

/** `GET /islem-kayitlari` kaydı. `ayrinti` sözleşme gereği sır içermez. */
export type IslemKaydi = {
  id: number;
  kullanici_id: number | null;
  kullanici_eposta: string | null;
  eylem: string;
  /** Boş dize: hedef türü yazılmamış. */
  hedef_tur: string;
  /** Sunucuda metin olarak saklanır (boş dize: hedef yok). */
  hedef_id: string;
  ayrinti: Record<string, unknown>;
  ip: string;
  olusturulma: string;
};

export type IslemFiltresi = {
  /** Denetim eylemi adı (ör. `kullanici.guncelle`). */
  eylem: string;
  kullanici_id: number | null;
  /** `YYYY-AA-GG` (yerel gün); sunucuya UTC gün sınırı olarak gider. */
  baslangic: string;
  bitis: string;
  sayfa: number;
  boyut: number;
};

export const BASLANGIC_ISLEM_FILTRESI: IslemFiltresi = {
  eylem: "",
  kullanici_id: null,
  baslangic: "",
  bitis: "",
  sayfa: 1,
  boyut: VARSAYILAN_ISLEM_SAYFA_BOYUTU,
};

/**
 * `ayrinti` anahtarlarının katalog anahtarı karşılıkları (spec §10.2); bilinmeyen
 * anahtar olduğu gibi yazılır.
 */
export const AYRINTI_ANAHTARI: Record<string, SozlukAnahtari> = {
  ad: "islem.alan.ad",
  anahtarlar: "islem.alan.anahtarlar",
  api_anahtari_id: "islem.alan.api_anahtari_id",
  baslik: "islem.alan.baslik",
  bdm_id: "islem.alan.bdm_id",
  bdm_slug: "islem.alan.bdm_slug",
  durum: "islem.alan.durum",
  eposta: "islem.alan.eposta",
  gecersiz: "islem.alan.gecersiz",
  gun: "islem.alan.gun",
  izinli_modeller: "islem.alan.izinli_modeller",
  konusma_id: "islem.alan.konusma_id",
  kullanici_id: "islem.alan.kullanici_id",
  marka_adi: "islem.alan.marka_adi",
  rol: "islem.alan.rol",
  silinen: "islem.alan.silinen",
  slug: "islem.alan.slug",
};

/** Ayrıntı değerini tek satırda okunur biçime çevirir. */
export function ayrintiDegeri(deger: unknown): string {
  if (deger === null || deger === undefined) return "—";
  if (Array.isArray(deger)) return deger.length > 0 ? deger.map(ayrintiDegeri).join(", ") : "—";
  if (typeof deger === "object") return JSON.stringify(deger);
  if (typeof deger === "boolean") {
    return ceviri(deger ? "islem.evet" : "islem.hayir", aktifDil());
  }
  return String(deger);
}

export function islemSorgusu(filtre: IslemFiltresi): string {
  const parametreler = new URLSearchParams();
  const eylem = filtre.eylem.trim();
  if (eylem) parametreler.set("eylem", eylem);
  if (filtre.kullanici_id !== null) {
    parametreler.set("kullanici_id", String(filtre.kullanici_id));
  }
  const baslangic = gunSiniriIso(filtre.baslangic, false);
  const bitis = gunSiniriIso(filtre.bitis, true);
  if (baslangic) parametreler.set("baslangic", baslangic);
  if (bitis) parametreler.set("bitis", bitis);
  parametreler.set("sayfa", String(filtre.sayfa));
  parametreler.set("boyut", String(filtre.boyut));
  return parametreler.toString();
}

export async function islemKayitlariniGetir(filtre: IslemFiltresi): Promise<Sayfa<IslemKaydi>> {
  return istek<Sayfa<IslemKaydi>>(`/islem-kayitlari?${islemSorgusu(filtre)}`);
}
