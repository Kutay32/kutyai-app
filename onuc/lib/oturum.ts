/** Tarayıcı oturumunun jeton çifti. */
export type Oturum = {
  erisim_jetonu: string;
  yenileme_jetonu: string;
};

const ERISIM_ANAHTARI = "kutyai.erisim_jetonu";
const YENILEME_ANAHTARI = "kutyai.yenileme_jetonu";

function depo(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Kayıtlı oturumu döner; iki jeton da yoksa `null`. */
export function oturumAl(): Oturum | null {
  const d = depo();
  if (!d) return null;
  const erisim = d.getItem(ERISIM_ANAHTARI);
  const yenileme = d.getItem(YENILEME_ANAHTARI);
  if (!erisim || !yenileme) return null;
  return { erisim_jetonu: erisim, yenileme_jetonu: yenileme };
}

/** Oturum jetonlarını yazar; verilmeyen jeton korunur. */
export function oturumKaydet(oturum: Partial<Oturum>): void {
  const d = depo();
  if (!d) return;
  if (oturum.erisim_jetonu) d.setItem(ERISIM_ANAHTARI, oturum.erisim_jetonu);
  if (oturum.yenileme_jetonu) d.setItem(YENILEME_ANAHTARI, oturum.yenileme_jetonu);
}

/** Oturumu siler (çıkış veya yenileme başarısızlığı). */
export function temizle(): void {
  const d = depo();
  if (!d) return;
  d.removeItem(ERISIM_ANAHTARI);
  d.removeItem(YENILEME_ANAHTARI);
}
