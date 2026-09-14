import { trBdm, trKayitlar, trPanel, trYonetim } from "./parcalar";

/**
 * Türkçe mesaj kataloğu (spec §10.2).
 *
 * Kataloglar `parcalar/` altında grup grup tutulur ve burada birleştirilir;
 * her dilimin `en` karşılığı kendi dosyasında `Record<keyof typeof trX, string>`
 * ile zorunlu kılınır, `en.ts` ise birleşik bütünlüğü denetler.
 */
export const tr = {
  ...trPanel,
  ...trBdm,
  ...trKayitlar,
  ...trYonetim,
} as const;

/** Türkçe katalog tipi; `en.ts` bu anahtarların tamamını vermek zorundadır. */
export type Sozluk = typeof tr;
export type SozlukAnahtari = keyof Sozluk;
