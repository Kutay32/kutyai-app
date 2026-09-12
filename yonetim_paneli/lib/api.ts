import { kullaniciOku, oturumKaydet, oturumOku, oturumTemizle } from "@/lib/oturum";

export const API_TABANI = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

export type Yontem = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export type IstekSecenekleri = {
  yontem?: Yontem;
  govde?: unknown;
  /** `undefined` → kayıtlı erişim jetonu; `null` → kimliksiz istek. */
  jeton?: string | null;
  basliklar?: Record<string, string>;
  /** 401 alındığında tek yenileme denemesi yapılsın mı (varsayılan: evet). */
  yenile?: boolean;
  sinyal?: AbortSignal;
};

/** `kaynak/API.md` §1 hata zarfını taşıyan istemci hatası. */
export class ApiHatasi extends Error {
  readonly durum: number;
  readonly kod: string;
  readonly ayrinti: unknown;

  constructor(durum: number, kod: string, mesaj: string, ayrinti?: unknown) {
    super(mesaj);
    this.name = "ApiHatasi";
    this.durum = durum;
    this.kod = kod;
    this.ayrinti = ayrinti;
  }
}

const VARSAYILAN_MESAJLAR: Record<number, string> = {
  400: "Gönderilen bilgiler geçersiz.",
  401: "Oturum bilgisi geçersiz. Lütfen tekrar giriş yapın.",
  403: "Bu işlem için yetkiniz yok.",
  404: "Kayıt bulunamadı.",
  409: "Bu kayıt zaten mevcut.",
  422: "Gönderilen alanlar doğrulanamadı.",
  429: "Çok fazla istek gönderdiniz. Lütfen biraz bekleyin.",
  500: "Sunucuda beklenmeyen bir hata oluştu.",
  502: "Model sağlayıcısına ulaşılamadı.",
  503: "Servis şu anda kullanılamıyor.",
};

/** Kullanıcıya gösterilecek Türkçe hata metnini üretir. */
export function hataMesaji(hata: unknown): string {
  if (hata instanceof ApiHatasi) return hata.message;
  if (hata instanceof Error && hata.message.trim()) return hata.message;
  return "Beklenmeyen bir hata oluştu.";
}

/** Hata zarfını `{ hata: { kod, mesaj, ayrinti } }` biçiminden çözer. */
function zarfCoz(govde: unknown, durum: number): ApiHatasi {
  const hata = (govde as { hata?: { kod?: unknown; mesaj?: unknown; ayrinti?: unknown } } | null)
    ?.hata;
  const kod = typeof hata?.kod === "string" ? hata.kod : "bilinmeyen_hata";
  const mesaj =
    typeof hata?.mesaj === "string" && hata.mesaj.trim()
      ? hata.mesaj
      : (VARSAYILAN_MESAJLAR[durum] ?? "İstek tamamlanamadı.");
  return new ApiHatasi(durum, kod, mesaj, hata?.ayrinti);
}

async function hamIstek(yol: string, secenekler: IstekSecenekleri): Promise<Response> {
  const basliklar: Record<string, string> = { ...secenekler.basliklar };
  if (secenekler.govde !== undefined) basliklar["Content-Type"] = "application/json";

  const jeton = secenekler.jeton === undefined ? oturumOku("erisim") : secenekler.jeton;
  if (jeton) basliklar.Authorization = `Bearer ${jeton}`;

  try {
    return await fetch(`${API_TABANI}${yol}`, {
      method: secenekler.yontem ?? "GET",
      headers: basliklar,
      body: secenekler.govde === undefined ? undefined : JSON.stringify(secenekler.govde),
      cache: "no-store",
      signal: secenekler.sinyal,
    });
  } catch (hata) {
    if (hata instanceof Error && hata.name === "AbortError") throw hata;
    throw new ApiHatasi(
      0,
      "baglanti_hatasi",
      "Sunucuya ulaşılamadı. API adresini ve bağlantınızı kontrol edin.",
    );
  }
}

async function govdeCoz<T>(cevap: Response): Promise<T> {
  if (cevap.status === 204) return undefined as T;

  const icerikTuru = cevap.headers.get("content-type") ?? "";
  let govde: unknown = null;
  try {
    govde = icerikTuru.includes("json") ? await cevap.json() : await cevap.text();
  } catch {
    govde = null;
  }

  if (!cevap.ok) throw zarfCoz(govde, cevap.status);
  return govde as T;
}

// Aynı anda birden çok 401 gelirse tek yenileme isteği paylaşılır.
let yenilemeSozu: Promise<boolean> | null = null;

async function jetonuYenile(): Promise<boolean> {
  const yenileme = oturumOku("yenileme");
  if (!yenileme) return false;

  const istek = (async () => {
    const cevap = await fetch(`${API_TABANI}/kimlik/yenile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yenileme_jetonu: yenileme }),
      cache: "no-store",
    });
    if (!cevap.ok) return false;

    const veri = (await cevap.json()) as {
      erisim_jetonu?: string;
      yenileme_jetonu?: string;
    };
    const kullanici = kullaniciOku();
    if (!veri.erisim_jetonu || !veri.yenileme_jetonu || !kullanici) return false;

    oturumKaydet({
      erisim_jetonu: veri.erisim_jetonu,
      yenileme_jetonu: veri.yenileme_jetonu,
      kullanici,
    });
    return true;
  })().catch(() => false);

  yenilemeSozu = istek;
  try {
    return await istek;
  } finally {
    if (yenilemeSozu === istek) yenilemeSozu = null;
  }
}

/**
 * API çağrısı. 401 alınırsa yenileme jetonuyla **tek** kez yeniden dener;
 * yenileme başarısızsa oturum temizlenir ve hata yukarı taşınır.
 */
export async function istek<T>(yol: string, secenekler: IstekSecenekleri = {}): Promise<T> {
  const cevap = await hamIstek(yol, secenekler);

  if (cevap.status === 401 && secenekler.yenile !== false) {
    if (await jetonuYenile()) {
      return govdeCoz<T>(await hamIstek(yol, { ...secenekler, jeton: undefined, yenile: false }));
    }
    oturumTemizle();
  }

  return govdeCoz<T>(cevap);
}

/** Kimlik doğrulamalı dosya indirir (ör. log dışa aktarma). */
export async function dosyaIndir(yol: string, dosyaAdi: string): Promise<void> {
  const cevap = await hamIstek(yol, {});
  if (!cevap.ok) throw zarfCoz(null, cevap.status);

  const adres = URL.createObjectURL(await cevap.blob());
  const baglanti = document.createElement("a");
  baglanti.href = adres;
  baglanti.download = dosyaAdi;
  document.body.append(baglanti);
  baglanti.click();
  baglanti.remove();
  URL.revokeObjectURL(adres);
}
