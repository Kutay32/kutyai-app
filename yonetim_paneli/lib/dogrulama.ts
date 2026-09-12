/** Kurulum ve giriş formlarında kullanılan Türkçe doğrulama kuralları. */

const EPOSTA_DESENI = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export const EN_AZ_PAROLA_UZUNLUGU = 8;

/** Geçerliyse `null`, değilse gösterilecek Türkçe hata. */
export function epostaHatasi(deger: string): string | null {
  const temiz = deger.trim();
  if (!temiz) return "E-posta adresi zorunludur.";
  if (!EPOSTA_DESENI.test(temiz)) return "Geçerli bir e-posta adresi girin.";
  return null;
}

/** Geçerliyse `null`, değilse gösterilecek Türkçe hata. */
export function parolaHatasi(deger: string): string | null {
  if (!deger) return "Parola zorunludur.";
  if (deger.length < EN_AZ_PAROLA_UZUNLUGU) {
    return `Parola en az ${EN_AZ_PAROLA_UZUNLUGU} karakter olmalıdır.`;
  }
  return null;
}

/** Geçerliyse `null`, değilse gösterilecek Türkçe hata. */
export function parolaTekrarHatasi(parola: string, tekrar: string): string | null {
  if (!tekrar) return "Parola tekrarı zorunludur.";
  if (parola !== tekrar) return "Parolalar eşleşmiyor.";
  return null;
}

/** Geçerliyse `null`, değilse gösterilecek Türkçe hata. */
export function adresHatasi(deger: string): string | null {
  const temiz = deger.trim();
  if (!temiz) return "Temel adres zorunludur.";
  if (!/^https?:\/\//i.test(temiz)) return "Adres http:// veya https:// ile başlamalıdır.";
  return null;
}

/** Zorunlu metin alanı denetimi. */
export function zorunluHatasi(deger: string, etiket: string): string | null {
  return deger.trim() ? null : `${etiket} zorunludur.`;
}
