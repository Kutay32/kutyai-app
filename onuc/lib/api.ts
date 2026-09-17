import { oturumAl, oturumKaydet, temizle } from "./oturum";
import { aktifCeviri, tarayiciDili } from "./tarayici-dil";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** API hata zarfını (`{ hata: { kod, mesaj, ayrinti } }`) taşıyan istemci hatası. */
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

export type IstekSecenekleri = Omit<RequestInit, "body" | "headers"> & {
  /** JSON gövdesi (FormData verilirse olduğu gibi gönderilir). */
  govde?: unknown;
  basliklar?: Record<string, string>;
  /** Belirtilmezse kayıtlı oturum jetonu kullanılır. */
  jeton?: string | null;
  /** 401'de oturum yenileme denemesi yapılsın mı (giriş/kayıt uçlarında kapatılır). */
  yenilemeDene?: boolean;
  /** Yanıt gövdesini JSON yerine ham ikili (`Blob`) olarak döndürür (dosya indirme). */
  ham?: boolean;
};

function durumKodu(durum: number): string {
  if (durum === 400) return "gecersiz_istek";
  if (durum === 401) return "kimlik_gerekli";
  if (durum === 403) return "yetki_yok";
  if (durum === 404) return "bulunamadi";
  if (durum === 409) return "cakisma";
  if (durum === 429) return "oran_siniri";
  if (durum === 502) return "ust_saglayici_hatasi";
  if (durum === 503) return "bdm_hazir_degil";
  return "sunucu_hatasi";
}

async function hataUret(yanit: Response): Promise<ApiHatasi> {
  let zarf: unknown = null;
  try {
    zarf = await yanit.json();
  } catch {
    zarf = null;
  }
  const hata = (zarf as { hata?: { kod?: string; mesaj?: string; ayrinti?: unknown } } | null)?.hata;
  return new ApiHatasi(
    yanit.status,
    hata?.kod ?? durumKodu(yanit.status),
    hata?.mesaj ?? aktifCeviri("genel.hata.istek"),
    hata?.ayrinti,
  );
}

/** 401 alındığında tek seferlik oturum yenileme; eşzamanlı istekler aynı sözü bekler. */
let yenilemeSozu: Promise<boolean> | null = null;

async function jetonlariYenile(): Promise<boolean> {
  const oturum = oturumAl();
  if (!oturum?.yenileme_jetonu) return false;
  try {
    const yanit = await fetch(`${API_URL}/kimlik/yenile`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ yenileme_jetonu: oturum.yenileme_jetonu }),
    });
    if (!yanit.ok) return false;
    const veri = (await yanit.json()) as {
      erisim_jetonu?: string;
      yenileme_jetonu?: string;
    };
    if (!veri.erisim_jetonu || !veri.yenileme_jetonu) return false;
    oturumKaydet({
      erisim_jetonu: veri.erisim_jetonu,
      yenileme_jetonu: veri.yenileme_jetonu,
    });
    return true;
  } catch {
    return false;
  }
}

function oturumYenile(): Promise<boolean> {
  if (!yenilemeSozu) {
    yenilemeSozu = jetonlariYenile().finally(() => {
      yenilemeSozu = null;
    });
  }
  return yenilemeSozu;
}

function giriseYonlendir(): void {
  if (typeof window !== "undefined" && window.location.pathname !== "/giris") {
    window.location.assign("/giris");
  }
}

/** JSON API çağrısı: hata zarfını çözer, 401'de bir kez yeniler, gerekirse oturumu kapatır. */
export async function apiFetch<T>(yol: string, secenekler: IstekSecenekleri = {}): Promise<T> {
  const { govde, basliklar, jeton, yenilemeDene = true, ham = false, ...geriKalan } = secenekler;

  const gonder = async (kullanilanJeton: string | null): Promise<Response> => {
    const sonBasliklar: Record<string, string> = { Accept: "application/json", ...basliklar };
    // Sunucu hata/bilgi mesajları seçilen dilde dönsün (spec §10.1).
    sonBasliklar["Accept-Language"] = tarayiciDili();
    let sonGovde: BodyInit | undefined;
    if (govde instanceof FormData) {
      sonGovde = govde;
    } else if (govde !== undefined) {
      sonBasliklar["Content-Type"] = "application/json";
      sonGovde = JSON.stringify(govde);
    }
    if (kullanilanJeton) sonBasliklar.Authorization = `Bearer ${kullanilanJeton}`;
    try {
      return await fetch(`${API_URL}${yol}`, { ...geriKalan, headers: sonBasliklar, body: sonGovde });
    } catch {
      throw new ApiHatasi(0, "baglanti_hatasi", aktifCeviri("genel.hata.baglanti"));
    }
  };

  const baslangicJetonu = jeton === undefined ? (oturumAl()?.erisim_jetonu ?? null) : jeton;
  let yanit = await gonder(baslangicJetonu);

  if (yanit.status === 401 && yenilemeDene) {
    const yenilendi = await oturumYenile();
    if (yenilendi) {
      yanit = await gonder(oturumAl()?.erisim_jetonu ?? null);
    }
    if (!yenilendi || yanit.status === 401) {
      temizle();
      giriseYonlendir();
      throw await hataUret(yanit);
    }
  }

  if (!yanit.ok) throw await hataUret(yanit);
  if (yanit.status === 204) return undefined as T;
  if (ham) return (await yanit.blob()) as T;

  const tur = yanit.headers.get("content-type") ?? "";
  if (!tur.includes("application/json")) return undefined as T;
  return (await yanit.json()) as T;
}
