/** `kaynak/API.md` §15 organizasyon ve üyelik uçları istemcisi. */

import { aktifOrganizasyonOku } from "@/lib/aktif-organizasyon";
import { ApiHatasi, hataMesaji, istek } from "@/lib/api";
import { aktifDil, ceviri, type SozlukAnahtari } from "@/lib/sozluk";
import type {
  Organizasyon,
  OrganizasyonDurumu,
  OrganizasyonUyesi,
  UyelikDurumu,
  UyelikRolu,
} from "@/lib/tipler";

/** Form ve seçimlerde sunulan rol sırası (yetkiden yetkisize). */
export const UYELIK_ROLLERI: UyelikRolu[] = [
  "sahip",
  "yonetici",
  "operator",
  "izleyici",
  "son_kullanici",
];

export const UYELIK_DURUMLARI: UyelikDurumu[] = ["aktif", "beklemede", "pasif"];
export const ORGANIZASYON_DURUMLARI: OrganizasyonDurumu[] = ["aktif", "askida"];

/** Organizasyon yönetim yetkisi olan roller (arkauc `ORG_YONETIM_ROLLERI`). */
export const ORGANIZASYON_YONETIM_ROLLERI: UyelikRolu[] = ["sahip", "yonetici"];

export function organizasyonYonetebilirMi(rol: UyelikRolu | undefined): boolean {
  return rol !== undefined && ORGANIZASYON_YONETIM_ROLLERI.includes(rol);
}

/**
 * Organizasyon verisini yazma yetkisi olan roller: araç ve RAG uçları
 * (arkauc `YAZMA_ROLLERI` = yönetici + operatör; `sahip` her zaman yetkilidir).
 * Faturalama yazmaları bundan dardır, bkz. `organizasyonYonetebilirMi`.
 */
export const ORGANIZASYON_YAZMA_ROLLERI: UyelikRolu[] = ["sahip", "yonetici", "operator"];

export function organizasyonYazabilirMi(rol: UyelikRolu | undefined): boolean {
  return rol !== undefined && ORGANIZASYON_YAZMA_ROLLERI.includes(rol);
}

export type OrganizasyonIstegi = { ad: string; slug?: string };
export type OrganizasyonGuncellemesi = { ad?: string; durum?: OrganizasyonDurumu };
export type UyeIstegi = { eposta?: string; kullanici_id?: number; rol: UyelikRolu };
export type UyeGuncellemesi = { rol?: UyelikRolu; durum?: UyelikDurumu };

export function organizasyonlariGetir(): Promise<Organizasyon[]> {
  return istek<Organizasyon[]>("/organizasyonlar");
}

export function organizasyonOlustur(girdi: OrganizasyonIstegi): Promise<Organizasyon> {
  return istek<Organizasyon>("/organizasyonlar", { yontem: "POST", govde: girdi });
}

export function organizasyonGuncelle(
  organizasyonId: number,
  degisiklikler: OrganizasyonGuncellemesi,
): Promise<Organizasyon> {
  return istek<Organizasyon>(`/organizasyonlar/${organizasyonId}`, {
    yontem: "PATCH",
    govde: degisiklikler,
  });
}

export function uyeleriGetir(organizasyonId: number): Promise<OrganizasyonUyesi[]> {
  return istek<OrganizasyonUyesi[]>(`/organizasyonlar/${organizasyonId}/uyeler`);
}

export function uyeEkle(
  organizasyonId: number,
  girdi: UyeIstegi,
): Promise<OrganizasyonUyesi> {
  return istek<OrganizasyonUyesi>(`/organizasyonlar/${organizasyonId}/uyeler`, {
    yontem: "POST",
    govde: girdi,
  });
}

export function uyeGuncelle(
  organizasyonId: number,
  kullaniciId: number,
  degisiklikler: UyeGuncellemesi,
): Promise<OrganizasyonUyesi> {
  return istek<OrganizasyonUyesi>(
    `/organizasyonlar/${organizasyonId}/uyeler/${kullaniciId}`,
    { yontem: "PATCH", govde: degisiklikler },
  );
}

export async function uyeSil(organizasyonId: number, kullaniciId: number): Promise<void> {
  await istek<void>(`/organizasyonlar/${organizasyonId}/uyeler/${kullaniciId}`, {
    yontem: "DELETE",
  });
}

/** Aktif (etkin) sahip sayısı; "son sahip" koruması arayüzde bununla uygulanır. */
export function etkinSahipSayisi(uyeler: OrganizasyonUyesi[]): number {
  return uyeler.filter((uye) => uye.rol === "sahip" && uye.durum === "aktif").length;
}

/** Son etkin sahip mi? (rolü düşürülemez, durumu pasife alınamaz, silinemez) */
export function sonSahipMi(uye: OrganizasyonUyesi, uyeler: OrganizasyonUyesi[]): boolean {
  return uye.rol === "sahip" && uye.durum === "aktif" && etkinSahipSayisi(uyeler) <= 1;
}

const HATA_ANAHTARLARI: Record<string, SozlukAnahtari> = {
  gecersiz_gecis: "organizasyon.hata.gecersiz_gecis",
  yetki_yok: "organizasyon.hata.yetki_yok",
  org_erisim_yok: "organizasyon.hata.yetki_yok",
};

/**
 * Kurallara dayalı sunucu hatalarını (ör. `409 gecersiz_gecis`) aktif dilde
 * anlaşılır metne çevirir; diğer hatalarda sunucu mesajı korunur.
 */
export function organizasyonHatasi(hata: unknown): string {
  if (hata instanceof ApiHatasi) {
    const anahtar = HATA_ANAHTARLARI[hata.kod];
    if (anahtar) return ceviri(anahtar, aktifDil());
  }
  return hataMesaji(hata);
}

/**
 * Aktif organizasyon: kayıtlı seçim (slug) varsa o, yoksa kullanıcının ilk üyeliği.
 * Sunucu da `X-Organizasyon` başlığı yoksa aynı sırayı izler.
 */
export async function aktifOrganizasyon(): Promise<Organizasyon | null> {
  const organizasyonlar = await organizasyonlariGetir();
  const kayitli = aktifOrganizasyonOku();
  const bulunan = kayitli
    ? organizasyonlar.find((organizasyon) => organizasyon.slug === kayitli)
    : undefined;
  return bulunan ?? organizasyonlar[0] ?? null;
}

/** SSO giriş adresi gibi yerlerde kullanılacak aktif organizasyon slug'ı. */
export async function aktifOrganizasyonSlug(): Promise<string | null> {
  return (await aktifOrganizasyon())?.slug ?? null;
}

/** Aktif organizasyondaki rolüm; yönetim düğmelerini önden gizlemek için. */
export async function aktifOrganizasyonRolu(): Promise<UyelikRolu | null> {
  return (await aktifOrganizasyon())?.rol ?? null;
}
