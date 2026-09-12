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

/** Yenileme denemesinin sonucu: yalnız `gecersiz` oturumu sonlandırır. */
type YenilemeSonucu = "basarili" | "gecersiz" | "ulasilamadi";

/** Oturumun gerçekten bittiğini gösteren hata kodları (API.md §1). */
const OTURUM_BITTI_KODLARI: Record<string, true> = {
  jeton_gecersiz: true,
  jeton_suresi_doldu: true,
  gecersiz_kimlik_bilgisi: true,
  kimlik_gerekli: true,
};

async function yenilemeDene(): Promise<YenilemeSonucu> {
  const yenileme = oturumOku("yenileme");
  if (!yenileme) return "gecersiz";

  let cevap: Response;
  try {
    cevap = await fetch(`${API_TABANI}/kimlik/yenile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yenileme_jetonu: yenileme }),
      cache: "no-store",
    });
  } catch {
    // Ağ hatası: jeton geçersizliği değil, oturum korunur.
    return "ulasilamadi";
  }

  if (!cevap.ok) {
    if (cevap.status === 401 || cevap.status === 403) return "gecersiz";
    const govde = (await cevap.json().catch(() => null)) as { hata?: { kod?: unknown } } | null;
    const kod = typeof govde?.hata?.kod === "string" ? govde.hata.kod : null;
    return kod && OTURUM_BITTI_KODLARI[kod] === true ? "gecersiz" : "ulasilamadi";
  }

  const veri = (await cevap.json().catch(() => null)) as {
    erisim_jetonu?: string;
    yenileme_jetonu?: string;
  } | null;
  const kullanici = kullaniciOku();
  if (!veri?.erisim_jetonu || !veri.yenileme_jetonu || !kullanici) return "gecersiz";

  oturumKaydet({
    erisim_jetonu: veri.erisim_jetonu,
    yenileme_jetonu: veri.yenileme_jetonu,
    kullanici,
  });
  return "basarili";
}

/** Uçuşta olan yenileme sözü: eşzamanlı 401'ler tek isteği paylaşır (single-flight). */
let yenilemeSozu: Promise<YenilemeSonucu> | null = null;

/**
 * Uçuşta bir yenileme varsa onu paylaşır; yoksa yenisini başlatır.
 * Böylece eşzamanlı 401 dalgası sunucuda yenileme jetonu rotasyonu yarışına girmez.
 */
function jetonuYenile(): Promise<YenilemeSonucu> {
  if (!yenilemeSozu) {
    const soz = yenilemeDene();
    yenilemeSozu = soz;
    void soz.then(() => {
      if (yenilemeSozu === soz) yenilemeSozu = null;
    });
  }
  return yenilemeSozu;
}

/**
 * 401 alındığında tekilleştirilmiş yenileme ve **tek** yeniden deneme uygular.
 * Oturum yalnızca yenileme jetonu gerçekten geçersizse temizlenir; ağ hatasında korunur.
 */
async function jetonluIstek(yol: string, secenekler: IstekSecenekleri): Promise<Response> {
  const kullanilanJeton = secenekler.jeton === undefined ? oturumOku("erisim") : secenekler.jeton;
  const cevap = await hamIstek(yol, secenekler);

  // Kimliksiz istek veya yenileme kapalı: oturuma dokunulmaz.
  if (cevap.status !== 401 || secenekler.yenile === false || secenekler.jeton === null) {
    return cevap;
  }

  // İstek bayat bir jetonla gitti ve bu arada başka bir yenileme tamamlandıysa
  // yenileme isteğini yinelemeye gerek yoktur; doğrudan güncel jetonla denenir.
  if (secenekler.jeton === undefined && kullanilanJeton) {
    const guncelJeton = oturumOku("erisim");
    if (guncelJeton && guncelJeton !== kullanilanJeton) {
      return hamIstek(yol, { ...secenekler, yenile: false });
    }
  }

  const sonuc = await jetonuYenile();
  if (sonuc === "basarili") return hamIstek(yol, { ...secenekler, yenile: false });
  if (sonuc === "gecersiz") oturumTemizle();
  return cevap;
}

/**
 * API çağrısı. 401 alınırsa yenileme jetonuyla **tek** kez yeniden dener;
 * yenileme jetonu geçersizse oturum temizlenir ve hata yukarı taşınır.
 */
export async function istek<T>(yol: string, secenekler: IstekSecenekleri = {}): Promise<T> {
  return govdeCoz<T>(await jetonluIstek(yol, secenekler));
}

/** Kimlik doğrulamalı dosya indirir (ör. log dışa aktarma). */
export async function dosyaIndir(yol: string, dosyaAdi: string): Promise<void> {
  const cevap = await jetonluIstek(yol, {});
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
