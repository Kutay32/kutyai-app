/**
 * Panelde aktif organizasyon seçimi (spec §15).
 *
 * Sunucu aktif organizasyonu `X-Organizasyon: <slug>` başlığından çözer
 * (`arkauc/app/cekirdek/organizasyon.py` → `ORG_BASLIGI`). Seçim burada
 * saklanır; `lib/api.ts` her isteğe başlığı ekler, `OrganizasyonSecici` de
 * jetonu `/kimlik/organizasyon-sec` ile tazeler.
 */

const ANAHTAR = "kutyai.panel.organizasyon";
const OLAY = "kutyai-organizasyon-degisti";

export function aktifOrganizasyonOku(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(ANAHTAR);
  } catch {
    return null;
  }
}

export function aktifOrganizasyonKaydet(slug: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (slug) window.localStorage.setItem(ANAHTAR, slug);
    else window.localStorage.removeItem(ANAHTAR);
  } catch {
    // Depo kapalı: seçim bellekte kalmaz, istekler varsayılan organizasyona gider.
  }
  window.dispatchEvent(new Event(OLAY));
}

/** Organizasyon değişimini dinler; abonelikten çıkma işlevi döner. */
export function organizasyonDegisiminiDinle(dinleyici: () => void): () => void {
  window.addEventListener(OLAY, dinleyici);
  window.addEventListener("storage", dinleyici);
  return () => {
    window.removeEventListener(OLAY, dinleyici);
    window.removeEventListener("storage", dinleyici);
  };
}
