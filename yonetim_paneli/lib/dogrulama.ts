/** Kurulum ve giriş formlarında kullanılan doğrulama kuralları (spec §10.2). */

import { aktifDil, ceviri } from "@/lib/sozluk";

const EPOSTA_DESENI = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const EN_AZ_PAROLA_UZUNLUGU = 8;

/** Geçerliyse `null`, değilse aktif dilde gösterilecek hata. */
export function epostaHatasi(deger: string): string | null {
  const temiz = deger.trim();
  if (!temiz) return ceviri("dogrulama.eposta.zorunlu", aktifDil());
  if (!EPOSTA_DESENI.test(temiz)) return ceviri("dogrulama.eposta.gecersiz", aktifDil());
  return null;
}

/** Geçerliyse `null`, değilse aktif dilde gösterilecek hata. */
export function parolaHatasi(deger: string): string | null {
  if (!deger) return ceviri("dogrulama.parola.zorunlu", aktifDil());
  if (deger.length < EN_AZ_PAROLA_UZUNLUGU) {
    return ceviri("dogrulama.parola.kisa", aktifDil(), { uzunluk: EN_AZ_PAROLA_UZUNLUGU });
  }
  return null;
}

/** Geçerliyse `null`, değilse aktif dilde gösterilecek hata. */
export function parolaTekrarHatasi(parola: string, tekrar: string): string | null {
  if (!tekrar) return ceviri("dogrulama.parola.tekrar_zorunlu", aktifDil());
  if (parola !== tekrar) return ceviri("dogrulama.parola.eslesmiyor", aktifDil());
  return null;
}

/** Geçerliyse `null`, değilse aktif dilde gösterilecek hata. */
export function adresHatasi(deger: string): string | null {
  const temiz = deger.trim();
  if (!temiz) return ceviri("dogrulama.adres.zorunlu", aktifDil());
  if (!/^https?:\/\//i.test(temiz)) return ceviri("dogrulama.adres.gecersiz", aktifDil());
  return null;
}

/** Zorunlu metin alanı denetimi. */
export function zorunluHatasi(deger: string, etiket: string): string | null {
  return deger.trim() ? null : ceviri("dogrulama.zorunlu", aktifDil(), { alan: etiket });
}
