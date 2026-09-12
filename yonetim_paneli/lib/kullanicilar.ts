/** `kaynak/API.md` §6 kullanıcı yönetimi istemcisi (yalnız yönetici). */

import { istek } from "@/lib/api";
import type { Kullanici, KullaniciDurumu, Rol, Sayfa } from "@/lib/tipler";

export const VARSAYILAN_KULLANICI_SAYFA_BOYUTU = 25;
export const KULLANICI_SAYFA_BOYUTLARI = [25, 50, 100] as const;

/** Form ve filtrelerde sunulan rol sırası (yetkiden yetkisize). */
export const ROLLER: Rol[] = ["yonetici", "operator", "izleyici", "son_kullanici"];
export const KULLANICI_DURUMLARI: KullaniciDurumu[] = ["aktif", "beklemede", "pasif"];


/** Boş dize "filtre yok" anlamına gelir (`<select>` uyumu için). */
export type KullaniciFiltresi = {
  rol: Rol | "";
  durum: KullaniciDurumu | "";
  arama: string;
  sayfa: number;
  boyut: number;
};

export const BASLANGIC_KULLANICI_FILTRESI: KullaniciFiltresi = {
  rol: "",
  durum: "",
  arama: "",
  sayfa: 1,
  boyut: VARSAYILAN_KULLANICI_SAYFA_BOYUTU,
};

export type KullaniciIstegi = {
  eposta: string;
  ad_soyad: string;
  parola: string;
  rol: Rol;
};

export type KullaniciGuncellemesi = {
  rol?: Rol;
  durum?: KullaniciDurumu;
  ad_soyad?: string;
};

export function kullaniciSorgusu(filtre: KullaniciFiltresi): string {
  const parametreler = new URLSearchParams();
  if (filtre.rol) parametreler.set("rol", filtre.rol);
  if (filtre.durum) parametreler.set("durum", filtre.durum);
  const arama = filtre.arama.trim();
  if (arama) parametreler.set("arama", arama);
  parametreler.set("sayfa", String(filtre.sayfa));
  parametreler.set("boyut", String(filtre.boyut));
  return parametreler.toString();
}

export async function kullanicilariGetir(
  filtre: KullaniciFiltresi,
): Promise<Sayfa<Kullanici>> {
  return istek<Sayfa<Kullanici>>(`/kullanicilar?${kullaniciSorgusu(filtre)}`);
}

export async function kullaniciOlustur(girdi: KullaniciIstegi): Promise<Kullanici> {
  return istek<Kullanici>("/kullanicilar", { yontem: "POST", govde: girdi });
}

export async function kullaniciGuncelle(
  kullaniciId: number,
  degisiklikler: KullaniciGuncellemesi,
): Promise<Kullanici> {
  return istek<Kullanici>(`/kullanicilar/${kullaniciId}`, {
    yontem: "PATCH",
    govde: degisiklikler,
  });
}

/** Silmez, pasifleştirir (açık oturumlar sunucuda iptal edilir). */
export async function kullaniciPasiflestir(kullaniciId: number): Promise<void> {
  await istek<void>(`/kullanicilar/${kullaniciId}`, { yontem: "DELETE" });
}

/** Karışıklık yaratan karakterleri (0/O, 1/l/I) dışarıda bırakan alfabe. */
const GECICI_PAROLA_ALFABESI = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";

/** Personel davetinde kullanılacak 12 karakterlik parola (kriptografik rastgele). */
export function geciciParolaUret(uzunluk = 12): string {
  const ham = new Uint32Array(uzunluk);
  crypto.getRandomValues(ham);
  return Array.from(ham, (deger) => GECICI_PAROLA_ALFABESI[deger % GECICI_PAROLA_ALFABESI.length]).join(
    "",
  );
}
