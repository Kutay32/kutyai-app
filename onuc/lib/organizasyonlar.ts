/** `kaynak/API.md` §15 organizasyon istemcisi: aktif organizasyonun üyelik rolü. */

import { apiFetch } from "./api";
import type { UyelikRolu } from "./tipler";

/** Organizasyon durumu; `askida` organizasyon uçlara kapalıdır. */
export type OrganizasyonDurumu = "aktif" | "askida";

/** `GET /organizasyonlar` satırı: kullanıcının üye olduğu organizasyon ve rolü. */
export type UyelikOzeti = {
  id: number;
  ad: string;
  slug: string;
  durum: OrganizasyonDurumu;
  /** Üyelik rolü; sunucu kaydı çözemezse `null` dönebilir. */
  rol: UyelikRolu | null;
  olusturulma: string | null;
};

/** Kullanıcının üye olduğu organizasyonlar (üyelik sırasıyla). */
export function organizasyonlariGetir(): Promise<UyelikOzeti[]> {
  return apiFetch<UyelikOzeti[]>("/organizasyonlar");
}

/**
 * Aktif organizasyonun üyelik rolü.
 *
 * Sunucu aktif organizasyonu `X-Organizasyon` → jeton `org` claim'i → ilk aktif
 * üyelik sırasıyla çözer ve yetkiyi **üyelik** rolünden verir (API.md §15).
 * `onuc` başlık göndermediği için jeton claim'iyle eşleşen satır, yoksa ilk
 * `aktif` organizasyon seçilir; liste boşsa `null` döner.
 */
export function aktifUyelikRolu(
  uyelikler: UyelikOzeti[],
  jetonOrganizasyonId: number | null,
): UyelikRolu | null {
  const jetonla =
    jetonOrganizasyonId === null
      ? undefined
      : uyelikler.find((uyelik) => uyelik.id === jetonOrganizasyonId);
  const secili =
    jetonla ?? uyelikler.find((uyelik) => uyelik.durum === "aktif") ?? uyelikler[0];
  return secili?.rol ?? null;
}
