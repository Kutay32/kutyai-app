import {
  trArac,
  trBdm,
  trBilgi,
  trDosya,
  trFaturalama,
  trKayitlar,
  trOrganizasyon,
  trPanel,
  trPosta,
  trSso,
  trYonetim,
} from "./parcalar";

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
  ...trOrganizasyon,
  ...trDosya,
  ...trBilgi,
  ...trArac,
  ...trFaturalama,
  ...trPosta,
  ...trSso,
} as const;

/** Türkçe katalog tipi; `en.ts` bu anahtarların tamamını vermek zorundadır. */
export type Sozluk = typeof tr;
export type SozlukAnahtari = keyof Sozluk;
