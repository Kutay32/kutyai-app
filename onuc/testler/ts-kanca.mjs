/**
 * Next.js kaynakları göreli içe aktarmaları uzantısız yazar (`./api`); Node'un ESM
 * çözümleyicisi bunları bulamaz. Bu kanca başarısız çözümlemede `.ts`/`.tsx`
 * uzantısını dener; böylece `npm test` uygulama modüllerini doğrudan yükler.
 */

const DENENEN_UZANTILAR = [".ts", ".tsx"];

export async function resolve(specifier, context, nextResolve) {
  try {
    return await nextResolve(specifier, context);
  } catch (hata) {
    if (!specifier.startsWith(".") || /\.[cm]?[jt]sx?$/.test(specifier)) throw hata;
    for (const uzanti of DENENEN_UZANTILAR) {
      try {
        return await nextResolve(`${specifier}${uzanti}`, context);
      } catch {
        // Sıradaki uzantı denenir.
      }
    }
    throw hata;
  }
}
