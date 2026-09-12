/** API'nin döndürdüğü `gelistirme_baglantisi` bağlantısından doğrulama/sıfırlama jetonunu ayıklar. */
export function baglantidanJeton(baglanti: string | undefined | null): string | null {
  if (!baglanti) return null;
  try {
    return new URL(baglanti).searchParams.get("jeton");
  } catch {
    return null;
  }
}
