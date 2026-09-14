import { en } from "./en";
import { tr, type Sozluk, type SozlukAnahtari } from "./tr";

export type { Sozluk, SozlukAnahtari };

export const VARSAYILAN_DIL = "tr";
export type Dil = "tr" | "en";
export const DESTEKLENEN_DILLER: readonly Dil[] = ["tr", "en"];
export const DIL_ADLARI: Record<Dil, string> = { tr: "Türkçe", en: "English" };

/** Dil tercihini taşıyan çerez; sunucu bileşenleri `<html lang>` için okur. */
export const DIL_CEREZI = "kutyai.dil";

const SOZLUKLER: Record<Dil, Record<SozlukAnahtari, string>> = { tr, en };

export function dilGecerliMi(deger: unknown): deger is Dil {
  return typeof deger === "string" && (DESTEKLENEN_DILLER as readonly string[]).includes(deger);
}

export type Degiskenler = Record<string, string | number>;

/**
 * Anahtarı verilen dilde çözer ve `{ad}` yer tutucularını doldurur.
 * Anahtar bulunamazsa TR metne, o da yoksa anahtarın kendisine düşer; geliştirme
 * derlemesinde eksik anahtar `console.warn` ile bildirilir (üretimde sessiz).
 */
export function ceviri(
  anahtar: SozlukAnahtari,
  dil: Dil = VARSAYILAN_DIL,
  degiskenler?: Degiskenler,
): string {
  const sablon: string | undefined =
    SOZLUKLER[dil]?.[anahtar] ?? SOZLUKLER[VARSAYILAN_DIL][anahtar];
  if (sablon === undefined) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(`[i18n] eksik anahtar: ${anahtar}`);
    }
    return anahtar;
  }
  if (!degiskenler) return sablon;
  return sablon.replace(/\{(\w+)\}/g, (tam, ad: string) =>
    ad in degiskenler ? String(degiskenler[ad]) : tam,
  );
}
