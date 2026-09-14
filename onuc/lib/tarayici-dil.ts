import {
  ceviri,
  DIL_CEREZI,
  dilGecerliMi,
  VARSAYILAN_DIL,
  type Degiskenler,
  type Dil,
  type SozlukAnahtari,
} from "./sozluk/index";

/**
 * React dışı istemci modülleri için dil çözümü (spec §10.2).
 *
 * `sunucu-dil.ts` aynı çerezi sunucu bileşenlerinde okur; burada tarayıcı
 * bağlamında (ör. `lib/api.ts` hata mesajları, SSE akışı) okunur. Sunucu/derleme
 * bağlamında `document` yoktur, varsayılan dil döner.
 */
export function tarayiciDili(): Dil {
  if (typeof document === "undefined") return VARSAYILAN_DIL;
  for (const cerez of document.cookie.split(";")) {
    const ayirac = cerez.indexOf("=");
    if (ayirac === -1) continue;
    if (cerez.slice(0, ayirac).trim() !== DIL_CEREZI) continue;
    const deger = cerez.slice(ayirac + 1).trim();
    return dilGecerliMi(deger) ? deger : VARSAYILAN_DIL;
  }
  return VARSAYILAN_DIL;
}

/** React bağlamı olmayan modüllerde aktif dilde çeviri çözer. */
export function aktifCeviri(anahtar: SozlukAnahtari, degiskenler?: Degiskenler): string {
  return ceviri(anahtar, tarayiciDili(), degiskenler);
}
