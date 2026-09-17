import { aktifOrganizasyonKaydet } from "@/lib/aktif-organizasyon";
import type { Kullanici } from "@/lib/tipler";

export type Oturum = {
  erisim_jetonu: string;
  yenileme_jetonu: string;
  kullanici: Kullanici;
};

type OturumAnahtari = "erisim" | "yenileme" | "kullanici";

const ONEK = "kutyai.panel";
const OLAY = "kutyai-oturum-degisti";

/** localStorage erişimi (SSR ve gizli mod güvenli). */
function oku(anahtar: OturumAnahtari): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(`${ONEK}.${anahtar}`);
  } catch {
    return null;
  }
}

function yaz(anahtar: OturumAnahtari, deger: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(`${ONEK}.${anahtar}`, deger);
  } catch {
    // Kota dolu veya depolama kapalı: oturum bellekte devam eder.
  }
}

function sil(anahtar: OturumAnahtari): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(`${ONEK}.${anahtar}`);
  } catch {
    // yoksay
  }
}

/** Ham jeton değerini okur; yoksa `null`. */
export function oturumOku(anahtar: OturumAnahtari): string | null {
  return oku(anahtar);
}

/** Saklanan kullanıcıyı çözer; bozuk kayıt sessizce yok sayılır. */
export function kullaniciOku(): Kullanici | null {
  const ham = oku("kullanici");
  if (!ham) return null;
  try {
    return JSON.parse(ham) as Kullanici;
  } catch {
    sil("kullanici");
    return null;
  }
}

export function oturumKaydet(oturum: Oturum): void {
  yaz("erisim", oturum.erisim_jetonu);
  yaz("yenileme", oturum.yenileme_jetonu);
  yaz("kullanici", JSON.stringify(oturum.kullanici));
  bildir();
}

export function oturumTemizle(): void {
  sil("erisim");
  sil("yenileme");
  sil("kullanici");
  // Organizasyon seçimi oturuma bağlıdır: sonraki oturumun ilk istekleri bayat
  // `X-Organizasyon` başlığıyla gitmesin diye çıkışta birlikte silinir.
  aktifOrganizasyonKaydet(null);
  bildir();
}

function bildir(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(OLAY));
}

/** Oturum değişimini (bu sekmede veya başka sekmede) dinler; abonelikten çıkma işlevi döner. */
export function oturumDegisiminiDinle(dinleyici: () => void): () => void {
  window.addEventListener(OLAY, dinleyici);
  window.addEventListener("storage", dinleyici);
  return () => {
    window.removeEventListener(OLAY, dinleyici);
    window.removeEventListener("storage", dinleyici);
  };
}
