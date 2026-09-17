/** `kaynak/API.md` §15 SSO uçları istemcisi (spec §7). */

import { API_TABANI, ApiHatasi, hataMesaji, istek } from "@/lib/api";
import { aktifDil, ceviri, type SozlukAnahtari } from "@/lib/sozluk";

export type SsoTuru = "oidc" | "saml";

export const SSO_TURLERI: SsoTuru[] = ["oidc", "saml"];

export const SSO_TURU_ANAHTARI: Record<SsoTuru, SozlukAnahtari> = {
  oidc: "sso.tur.oidc",
  saml: "sso.tur.saml",
};

/** `GET /sso/saglayicilar` satırı; `sir_tanimli` yalnız varlığı bildirir. */
export type SsoSaglayici = {
  id: number;
  tur: SsoTuru;
  ad: string;
  slug: string;
  etkin: boolean;
  /** Sunucu `secret`/`sifre` içeren anahtarları ayıklar. */
  ayarlar: Record<string, string>;
  sir_tanimli: boolean;
  /** Sunucudan gelen yol şablonu: `/api/v1/sso/{org}/{slug}/baslat`. */
  giris_yolu: string;
  olusturulma: string | null;
};

/** `POST /sso/saglayicilar` gövdesi. */
export type SsoOlusturma = {
  tur: SsoTuru;
  ad: string;
  slug?: string;
  etkin: boolean;
  ayarlar: Record<string, string>;
  /** İstemci sırrı; `ayarlar` içine değil buraya yazılır (şifrelenir). */
  sir?: string;
};

/** `PATCH /sso/saglayicilar/{id}` gövdesi; `ayarlar` sunucuda birleştirilir. */
export type SsoGuncellemesi = {
  ad?: string;
  etkin?: boolean;
  ayarlar?: Record<string, string>;
  sir?: string;
};

export type SsoAlani = {
  anahtar: string;
  etiket: SozlukAnahtari;
  ipucu?: SozlukAnahtari;
  zorunlu?: boolean;
  cok_satirli?: boolean;
};

/** `sso_oidc.py` içinde okunan `ayarlar` anahtarları. */
export const OIDC_ALANLARI: SsoAlani[] = [
  { anahtar: "issuer", etiket: "sso.alan.issuer", ipucu: "sso.ipucu.issuer", zorunlu: true },
  {
    anahtar: "client_id",
    etiket: "sso.alan.client_id",
    ipucu: "sso.ipucu.client_id",
    zorunlu: true,
  },
  { anahtar: "kapsamlar", etiket: "sso.alan.kapsamlar", ipucu: "sso.ipucu.kapsamlar" },
  {
    anahtar: "eposta_claim",
    etiket: "sso.alan.eposta_claim",
    ipucu: "sso.ipucu.eposta_claim",
  },
  { anahtar: "ad_claim", etiket: "sso.alan.ad_claim", ipucu: "sso.ipucu.ad_claim" },
];

/** `sso_saml.py` içinde okunan `ayarlar` anahtarları. */
export const SAML_ALANLARI: SsoAlani[] = [
  {
    anahtar: "idp_sso_url",
    etiket: "sso.alan.idp_sso_url",
    ipucu: "sso.ipucu.idp_sso_url",
    zorunlu: true,
  },
  { anahtar: "sp_entity_id", etiket: "sso.alan.sp_entity_id", ipucu: "sso.ipucu.sp_entity_id" },
  {
    anahtar: "idp_imza_sertifikasi",
    etiket: "sso.alan.idp_imza_sertifikasi",
    ipucu: "sso.ipucu.idp_imza_sertifikasi",
    zorunlu: true,
    cok_satirli: true,
  },
  {
    anahtar: "eposta_ozniteligi",
    etiket: "sso.alan.eposta_ozniteligi",
    ipucu: "sso.ipucu.eposta_ozniteligi",
  },
  { anahtar: "ad_ozniteligi", etiket: "sso.alan.ad_ozniteligi", ipucu: "sso.ipucu.ad_ozniteligi" },
];

export function turAlanlari(tur: SsoTuru): SsoAlani[] {
  return tur === "oidc" ? OIDC_ALANLARI : SAML_ALANLARI;
}

/** Yeni sağlayıcı formu için boş `ayarlar` gövdesi. */
export function bosAyarlar(tur: SsoTuru): Record<string, string> {
  const ayarlar: Record<string, string> = {};
  for (const alan of turAlanlari(tur)) ayarlar[alan.anahtar] = "";
  return ayarlar;
}

/** Aynı değerdeki alanlar PUT/PATCH gövdesine girmez; boşlar da gönderilmez. */
export function doluAyarlar(ayarlar: Record<string, string>): Record<string, string> {
  const sonuc: Record<string, string> = {};
  for (const [anahtar, deger] of Object.entries(ayarlar)) {
    const temiz = deger.trim();
    if (temiz) sonuc[anahtar] = temiz;
  }
  return sonuc;
}

export function saglayicilariGetir(): Promise<SsoSaglayici[]> {
  return istek<SsoSaglayici[]>("/sso/saglayicilar");
}

export function saglayiciOlustur(girdi: SsoOlusturma): Promise<SsoSaglayici> {
  return istek<SsoSaglayici>("/sso/saglayicilar", { yontem: "POST", govde: girdi });
}

export function saglayiciGuncelle(
  saglayiciId: number,
  degisiklikler: SsoGuncellemesi,
): Promise<SsoSaglayici> {
  return istek<SsoSaglayici>(`/sso/saglayicilar/${saglayiciId}`, {
    yontem: "PATCH",
    govde: degisiklikler,
  });
}

export async function saglayiciSil(saglayiciId: number): Promise<void> {
  await istek<void>(`/sso/saglayicilar/${saglayiciId}`, { yontem: "DELETE" });
}

/**
 * Kullanıcıya gösterilecek tam giriş adresi. Sunucunun `giris_yolu` şablonundaki
 * `{org}` yerine aktif organizasyon slug'ı yazılır.
 */
export function girisAdresi(saglayici: SsoSaglayici, organizasyonSlug: string): string {
  return `${API_TABANI}/sso/${organizasyonSlug}/${saglayici.slug}/baslat`;
}

const HATA_ANAHTARLARI: Record<string, SozlukAnahtari> = {
  sso_yapilandirilmamis: "sso.hata.yapilandirilmamis",
  yetki_yok: "sso.hata.yetki_yok",
  org_erisim_yok: "sso.hata.yetki_yok",
};

/** SSO hata kodlarını aktif dilde anlaşılır metne çevirir. */
export function ssoHatasi(hata: unknown): string {
  if (hata instanceof ApiHatasi) {
    const anahtar = HATA_ANAHTARLARI[hata.kod];
    if (anahtar) return ceviri(anahtar, aktifDil());
  }
  return hataMesaji(hata);
}
