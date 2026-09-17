/** `kaynak/API.md` §15 posta şablonu uçları istemcisi (spec §9). */

import { ApiHatasi, hataMesaji, istek } from "@/lib/api";
import { aktifDil, ceviri, type SozlukAnahtari } from "@/lib/sozluk";

/** Sunucudaki `posta_sablon.KODLAR` ile birebir aynı sıra. */
export const SABLON_KODLARI = [
  "dogrulama",
  "sifirlama",
  "davet",
  "kota_uyarisi",
  "fatura",
  "hosgeldin",
] as const;

export type SablonKodu = (typeof SABLON_KODLARI)[number];

/** Sunucudaki `posta_sablonlari.DILLER` ile aynı. */
export const SABLON_DILLERI = ["tr", "en"] as const;

export type SablonDili = (typeof SABLON_DILLERI)[number];

/** `GET /posta-sablonlari` satırı; `ozel` false ise gömülü varsayılan gösterilir. */
export type PostaSablonu = {
  kod: SablonKodu;
  dil: SablonDili;
  konu: string;
  govde_metin: string;
  govde_html: string;
  ozel: boolean;
};

/** `PUT /posta-sablonlari` gövdesi. */
export type SablonKaydi = {
  kod: SablonKodu;
  dil: SablonDili;
  konu: string;
  govde_metin: string;
  govde_html: string;
};

/** `POST /posta-sablonlari/{kod}/onizle` yanıtı. */
export type SablonOnizlemesi = {
  kod: SablonKodu;
  dil: SablonDili;
  konu: string;
  govde_metin: string;
  govde_html: string;
};

export const SABLON_KODU_ANAHTARI: Record<SablonKodu, SozlukAnahtari> = {
  dogrulama: "posta.kod.dogrulama",
  sifirlama: "posta.kod.sifirlama",
  davet: "posta.kod.davet",
  kota_uyarisi: "posta.kod.kota_uyarisi",
  fatura: "posta.kod.fatura",
  hosgeldin: "posta.kod.hosgeldin",
};

export const SABLON_DILI_ANAHTARI: Record<SablonDili, SozlukAnahtari> = {
  tr: "posta.dil.tr",
  en: "posta.dil.en",
};

/** Sunucudaki yer tutucu deseni: `{{degisken}}` (`posta_sablon.DEGISKEN_DESENI`). */
const DEGISKEN_DESENI = /\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g;

/** Şablon metinlerinde geçen benzersiz değişken adları (ilk görülme sırasıyla). */
export function degiskenleriBul(...metinler: (string | null | undefined)[]): string[] {
  const bulunan: string[] = [];
  for (const metin of metinler) {
    if (!metin) continue;
    DEGISKEN_DESENI.lastIndex = 0;
    let eslesme = DEGISKEN_DESENI.exec(metin);
    while (eslesme !== null) {
      const ad = eslesme[1];
      if (ad && !bulunan.includes(ad)) bulunan.push(ad);
      eslesme = DEGISKEN_DESENI.exec(metin);
    }
  }
  return bulunan;
}

export function sablonlariGetir(): Promise<PostaSablonu[]> {
  return istek<PostaSablonu[]>("/posta-sablonlari");
}

export function sablonKaydet(girdi: SablonKaydi): Promise<PostaSablonu> {
  return istek<PostaSablonu>("/posta-sablonlari", { yontem: "PUT", govde: girdi });
}

/**
 * Kayıtlı şablonu örnek değerlerle doldurur. Verilen değişkenler sunucudaki
 * örnek değerleri geçersiz kılar; verilmeyenler örnek değerde kalır.
 */
export function sablonOnizle(
  kod: SablonKodu,
  dil: SablonDili,
  degiskenler?: Record<string, string>,
): Promise<SablonOnizlemesi> {
  return istek<SablonOnizlemesi>(`/posta-sablonlari/${kod}/onizle`, {
    yontem: "POST",
    govde: { dil, degiskenler: degiskenler && Object.keys(degiskenler).length ? degiskenler : null },
  });
}

const HATA_ANAHTARLARI: Record<string, SozlukAnahtari> = {
  bulunamadi: "posta.hata.bulunamadi",
  yetki_yok: "posta.hata.yetki_yok",
  org_erisim_yok: "posta.hata.yetki_yok",
};

/** Posta şablonu hatalarını aktif dilde anlaşılır metne çevirir. */
export function sablonHatasi(hata: unknown): string {
  if (hata instanceof ApiHatasi) {
    const anahtar = HATA_ANAHTARLARI[hata.kod];
    if (anahtar) return ceviri(anahtar, aktifDil());
  }
  return hataMesaji(hata);
}
