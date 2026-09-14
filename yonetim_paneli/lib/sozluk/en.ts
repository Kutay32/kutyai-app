import { enBdm, enKayitlar, enPanel, enYonetim } from "./parcalar";
import type { Sozluk } from "./tr";

/**
 * İngilizce mesaj kataloğu (spec §10.2). `Record<keyof Sozluk, string>` olduğu
 * için TR'de olup burada olmayan anahtar derleme hatası verir.
 */
export const en: Record<keyof Sozluk, string> = {
  ...enPanel,
  ...enBdm,
  ...enKayitlar,
  ...enYonetim,
};
