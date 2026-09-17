/** `kaynak/API.md` §19 araç istemcisi. */

import { ApiHatasi, istek } from "@/lib/api";
import type { Sayfa } from "@/lib/tipler";

export type AracTuru = "webhook" | "yerlesik";
export type AracCagrisiDurumu = "basarili" | "hata";

/**
 * Yerleşik araç slug'ları; tek doğru kaynak `arkauc/app/servisler/arac.py`
 * içindeki `YERLESIK_SEMALAR` (API.md §19).
 */
export const YERLESIK_SLUGLAR = ["hesap_makinesi", "zaman"] as const;

export const ARAC_TURLERI: AracTuru[] = ["webhook", "yerlesik"];
export const VARSAYILAN_ARAC_SAYFA_BOYUTU = 25;
export const ARAC_SAYFA_BOYUTLARI = [25, 50, 100] as const;

/** `GET /araclar` satırı; `basliklar` sunucuda maskelenmiş gelir. */
export type Arac = {
  id: number;
  ad: string;
  slug: string;
  aciklama: string;
  json_sema: Record<string, unknown>;
  tur: AracTuru;
  uc_noktasi: string;
  basliklar: Record<string, string>;
  etkin: boolean;
  olusturulma: string | null;
  guncellenme: string | null;
};

/** `POST /araclar` ve `PATCH /araclar/{id}` gövdesi. */
export type AracIstegi = {
  ad: string;
  slug?: string;
  aciklama?: string;
  json_sema?: Record<string, unknown>;
  tur: AracTuru;
  uc_noktasi?: string;
  basliklar?: Record<string, string>;
  etkin?: boolean;
};

/** `POST /araclar/{id}/dene` yanıtı (`ad` alanı aracın slug'ıdır). */
export type DenemeSonucu = {
  arac_id: number;
  ad: string;
  durum: AracCagrisiDurumu;
  sonuc: Record<string, unknown>;
  gecikme_ms: number;
};

/** `GET /araclar/cagrilar` satırı; araç silinirse `arac_id` boşalır. */
export type AracCagrisi = {
  id: number;
  arac_id: number | null;
  ad: string;
  konusma_id: number | null;
  mesaj_id: number | null;
  argumanlar: Record<string, unknown>;
  sonuc: Record<string, unknown>;
  durum: AracCagrisiDurumu;
  gecikme_ms: number;
  hata: string | null;
  olusturulma: string | null;
};

export type CagriFiltresi = {
  arac_id: number | null;
  /** Boş dize "tüm durumlar" anlamına gelir (`<select>` uyumu için). */
  durum: AracCagrisiDurumu | "";
  sayfa: number;
  boyut: number;
};

export const BASLANGIC_CAGRI_FILTRESI: CagriFiltresi = {
  arac_id: null,
  durum: "",
  sayfa: 1,
  boyut: VARSAYILAN_ARAC_SAYFA_BOYUTU,
};

/** Test formunu şemadan üretmek için sadeleştirilmiş alan tanımı. */
export type SemaAlani = {
  ad: string;
  /** JSON Schema `type` değeri; yoksa `string` varsayılır. */
  tur: string;
  zorunlu: boolean;
  aciklama: string;
};

export function cagriSorgusu(filtre: CagriFiltresi): string {
  const parametreler = new URLSearchParams();
  if (filtre.arac_id !== null) parametreler.set("arac_id", String(filtre.arac_id));
  if (filtre.durum) parametreler.set("durum", filtre.durum);
  parametreler.set("sayfa", String(filtre.sayfa));
  parametreler.set("boyut", String(filtre.boyut));
  return parametreler.toString();
}

/** Aracın JSON şemasından deneme formu alanlarını çıkarır. */
export function semaAlanlari(sema: Record<string, unknown> | null | undefined): SemaAlani[] {
  const ozellikler = (sema?.properties ?? {}) as Record<string, unknown>;
  const zorunlular = new Set(
    Array.isArray(sema?.required) ? (sema?.required as unknown[]).map(String) : [],
  );
  return Object.entries(ozellikler).map(([ad, ham]) => {
    const tanim = (ham ?? {}) as { type?: unknown; description?: unknown };
    return {
      ad,
      tur: typeof tanim.type === "string" ? tanim.type : "string",
      zorunlu: zorunlular.has(ad),
      aciklama: typeof tanim.description === "string" ? tanim.description : "",
    };
  });
}

/**
 * Webhook/çalıştırma hatasının teknik gerekçesini (`ayrinti.neden`) döndürür.
 * Sunucu zaman aşımı/durum kodu gibi nedenleri burada taşır (API.md §19).
 */
export function hataNedeni(sebep: unknown): string | null {
  if (!(sebep instanceof ApiHatasi)) return null;
  const ayrinti = sebep.ayrinti as { neden?: unknown } | null;
  if (ayrinti && typeof ayrinti.neden === "string" && ayrinti.neden.trim()) {
    return ayrinti.neden;
  }
  return null;
}

/** Aktif organizasyonun araçları; `etkin` verilirse etkinlik ile süzülür. */
export async function araclariGetir(etkin: boolean | null = null): Promise<Arac[]> {
  const sorgu = etkin === null ? "" : `?etkin=${etkin ? "true" : "false"}`;
  return istek<Arac[]>(`/araclar${sorgu}`);
}

export async function aracOlustur(girdi: AracIstegi): Promise<Arac> {
  return istek<Arac>("/araclar", { yontem: "POST", govde: girdi });
}

export async function aracGuncelle(aracId: number, girdi: AracIstegi): Promise<Arac> {
  return istek<Arac>(`/araclar/${aracId}`, { yontem: "PATCH", govde: girdi });
}

/**
 * Yalnız etkinlik alanını günceller; uç noktası/tür yeniden doğrulanmasın diye
 * gövde asgaride tutulur (API.md §19).
 */
export async function aracEtkinlikAyarla(aracId: number, etkin: boolean): Promise<Arac> {
  return istek<Arac>(`/araclar/${aracId}`, { yontem: "PATCH", govde: { etkin } });
}

/** Aracı siler; geçmiş çağrı kayıtları korunur. */
export async function aracSil(aracId: number): Promise<void> {
  await istek<void>(`/araclar/${aracId}`, { yontem: "DELETE" });
}

/**
 * Aracı verilen argümanlarla çalıştırır.
 * Argüman şema ihlali `400`, çalıştırma hatası `502 arac_hatasi` döner.
 */
export async function aracDene(
  aracId: number,
  argumanlar: Record<string, unknown>,
): Promise<DenemeSonucu> {
  return istek<DenemeSonucu>(`/araclar/${aracId}/dene`, {
    yontem: "POST",
    govde: { argumanlar },
  });
}

/** Araç çağrı günlüğü (yeni kayıt önce). */
export async function cagrilariGetir(filtre: CagriFiltresi): Promise<Sayfa<AracCagrisi>> {
  return istek<Sayfa<AracCagrisi>>(`/araclar/cagrilar?${cagriSorgusu(filtre)}`);
}
