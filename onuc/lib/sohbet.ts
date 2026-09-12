/**
 * Sohbet uçları (API.md §9): model listesi, konuşma geçmişi ve SSE akışı.
 *
 * Akış `fetch` + `ReadableStream` ile okunur; çerçeve çözümlemesi saf fonksiyon
 * (`cerceveleriCoz`) olarak ayrıldığı için ağ olmadan sınanabilir.
 */

import { ApiHatasi, API_URL, apiFetch } from "./api";
import { oturumAl } from "./oturum";
import type { Kullanici } from "./tipler";

/** API.md §2 `BdmOzet` — `/modeller` yanıtının kaydı. */
export type BdmOzet = {
  id: number;
  slug: string;
  gorunen_ad: string;
  aciklama: string;
  saglayici: string;
  baglam_penceresi: number;
  yetenekler: { akis?: boolean; gorsel?: boolean; arac?: boolean };
  durum: string;
};

/** `GET /sohbet/konusmalar` kaydı. */
export type KonusmaOzeti = {
  id: number;
  baslik: string;
  bdm_id: number;
  bdm_ad: string;
  guncellenme: string;
  mesaj_sayisi: number;
  token_girdi: number;
  token_cikti: number;
};

/** `GET /sohbet/konusmalar/{id}` mesaj kaydı. */
export type KonusmaMesaji = {
  id: number;
  rol: string;
  icerik: string;
  token_sayisi: number | null;
  gecikme_ms: number | null;
  olusturulma: string;
};

export type KonusmaDetayi = {
  id: number;
  baslik: string;
  bdm_id: number;
  olusturulma: string;
  mesajlar: KonusmaMesaji[];
};

export type SohbetAkisiIstegi = {
  bdm_id: number;
  konusma_id: number | null;
  mesaj: string;
  sistem_istemi?: string | null;
  sicaklik?: number | null;
  maks_token?: number | null;
};

/** Ekranda gösterilen mesaj: geçmiş kayıtları ile canlı akışın birleşimi. */
export type GorunumMesaji = {
  id: string;
  rol: "kullanici" | "asistan";
  icerik: string;
  /** Yanıt hâlâ akmakta (imleç gösterilir). */
  akisHalinde?: boolean;
  /** Kullanıcı üretimi durdurdu; yarım metin korundu. */
  durduruldu?: boolean;
  /** Akış hata ile bitti. */
  hatali?: boolean;
};

/** `/sohbet/akis` olayları (API.md §9 SSE biçimi). */
export type SohbetOlayi =
  | { tur: "baslangic"; konusma_id: number; mesaj_id: number }
  | { tur: "parca"; icerik: string }
  | { tur: "kullanim"; token_girdi: number; token_cikti: number; gecikme_ms: number }
  | { tur: "hata"; kod: string; mesaj: string; ayrinti: unknown }
  | { tur: "bitti" }
  | { tur: "gecersiz"; ad: string; ham: string };

const SECILI_MODEL_ANAHTARI = "kutyai.secili_model";

/* ------------------------------------------------- istemci tercihleri */

/** Kayıtlı model seçimi; yoksa/bozuksa `null`. */
export function seciliModeliAl(): number | null {
  if (typeof window === "undefined") return null;
  try {
    const ham = window.localStorage.getItem(SECILI_MODEL_ANAHTARI);
    if (!ham) return null;
    const deger = Number.parseInt(ham, 10);
    return Number.isFinite(deger) ? deger : null;
  } catch {
    return null;
  }
}

/** Model seçimini tarayıcıda kalıcılaştırır. */
export function seciliModeliKaydet(bdmId: number): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SECILI_MODEL_ANAHTARI, String(bdmId));
  } catch {
    // Depolama kapalıysa seçim yalnız bu oturumda yaşar.
  }
}

/* ---------------------------------------------------- SSE çözümlemesi */

/** Tek bir SSE çerçevesini (`event:`/`data:` satırları) olaya çevirir. */
function cerceveCoz(cerceve: string): SohbetOlayi | null {
  let ad = "mesaj";
  const veriSatirlari: string[] = [];
  for (const satir of cerceve.split(/\r?\n/)) {
    if (!satir || satir.startsWith(":")) continue;
    const ayirac = satir.indexOf(":");
    const alan = ayirac === -1 ? satir : satir.slice(0, ayirac);
    let deger = ayirac === -1 ? "" : satir.slice(ayirac + 1);
    if (deger.startsWith(" ")) deger = deger.slice(1);
    if (alan === "event") ad = deger;
    else if (alan === "data") veriSatirlari.push(deger);
  }
  if (veriSatirlari.length === 0) return null;
  const ham = veriSatirlari.join("\n");

  let paket: unknown;
  try {
    paket = JSON.parse(ham);
  } catch {
    return { tur: "gecersiz", ad, ham };
  }
  const kayit = (paket ?? {}) as Record<string, unknown>;

  if (ad === "baslangic") {
    const konusmaId = Number(kayit.konusma_id);
    const mesajId = Number(kayit.mesaj_id);
    if (!Number.isFinite(konusmaId)) return { tur: "gecersiz", ad, ham };
    return { tur: "baslangic", konusma_id: konusmaId, mesaj_id: mesajId };
  }
  if (ad === "parca") {
    const icerik = kayit.icerik;
    return { tur: "parca", icerik: typeof icerik === "string" ? icerik : "" };
  }
  if (ad === "kullanim") {
    return {
      tur: "kullanim",
      token_girdi: Number(kayit.token_girdi) || 0,
      token_cikti: Number(kayit.token_cikti) || 0,
      gecikme_ms: Number(kayit.gecikme_ms) || 0,
    };
  }
  if (ad === "hata") {
    const zarf = (kayit.hata ?? {}) as { kod?: unknown; mesaj?: unknown; ayrinti?: unknown };
    return {
      tur: "hata",
      kod: typeof zarf.kod === "string" ? zarf.kod : "sunucu_hatasi",
      mesaj: typeof zarf.mesaj === "string" ? zarf.mesaj : "Yanıt üretilemedi.",
      ayrinti: zarf.ayrinti,
    };
  }
  if (ad === "bitti") return { tur: "bitti" };
  return { tur: "gecersiz", ad, ham };
}

/**
 * Gelen metin parçasını çerçevelere böler.
 *
 * Parçalar ağdan rastgele sınırlarla geldiği için tamamlanmamış kuyruk
 * `kalan` olarak geri döner ve sonraki parçayla birleştirilir.
 */
export function cerceveleriCoz(tampon: string): {
  olaylar: SohbetOlayi[];
  kalan: string;
} {
  const parcalar = tampon.split(/\r?\n\r?\n/);
  const kalan = parcalar.pop() ?? "";
  const olaylar: SohbetOlayi[] = [];
  for (const parca of parcalar) {
    const olay = cerceveCoz(parca);
    if (olay) olaylar.push(olay);
  }
  return { olaylar, kalan };
}

/** HTTP hata yanıtını (hata zarfı veya düz metin) istemci hatasına çevirir. */
async function akisHatasi(yanit: Response): Promise<ApiHatasi> {
  let zarf: unknown = null;
  try {
    zarf = await yanit.json();
  } catch {
    zarf = null;
  }
  const hata = (zarf as { hata?: { kod?: string; mesaj?: string; ayrinti?: unknown } } | null)
    ?.hata;
  return new ApiHatasi(
    yanit.status,
    hata?.kod ?? "sunucu_hatasi",
    hata?.mesaj ?? "Yanıt alınamadı. Lütfen tekrar deneyin.",
    hata?.ayrinti,
  );
}

async function akisIstegi(istek: SohbetAkisiIstegi, sinyal?: AbortSignal): Promise<Response> {
  const gonder = async (jeton: string | null): Promise<Response> => {
    const basliklar: Record<string, string> = {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    };
    if (jeton) basliklar.Authorization = `Bearer ${jeton}`;
    try {
      return await fetch(`${API_URL}/sohbet/akis`, {
        method: "POST",
        headers: basliklar,
        body: JSON.stringify(istek),
        signal: sinyal,
      });
    } catch (hata) {
      if (sinyal?.aborted) throw hata;
      throw new ApiHatasi(0, "baglanti_hatasi", "Sunucuya ulaşılamadı. Bağlantınızı denetleyin.");
    }
  };

  let yanit = await gonder(oturumAl()?.erisim_jetonu ?? null);
  if (yanit.status === 401) {
    // `apiFetch` 401'de jetonu bir kez yeniler; akış isteği bu davranışı paylaşmadığı
    // için yenileme aynı yoldan tetiklenir, ardından akış bir kez tekrarlanır.
    try {
      await apiFetch<Kullanici>("/kimlik/ben");
    } catch {
      // Yenileme başarısızsa akış yanıtındaki hata zarfı kullanıcıya gösterilir.
    }
    yanit = await gonder(oturumAl()?.erisim_jetonu ?? null);
  }
  if (!yanit.ok) throw await akisHatasi(yanit);
  return yanit;
}

/**
 * `/sohbet/akis` akışını başlatır ve olayları sırayla `olayIsle`ye verir.
 *
 * `sinyal` iptal edildiğinde okuma `AbortError` ile biter; çağıran taraf o ana
 * kadar biriken metni korur (Durdur davranışı).
 */
export async function sohbetAkisiniBaslat(
  istek: SohbetAkisiIstegi,
  olayIsle: (olay: SohbetOlayi) => void,
  sinyal?: AbortSignal,
): Promise<void> {
  const yanit = await akisIstegi(istek, sinyal);
  const govde = yanit.body;
  if (!govde) {
    throw new ApiHatasi(yanit.status, "akis_yok", "Yanıt akışı okunamadı.");
  }

  const okuyucu = govde.getReader();
  const cozucu = new TextDecoder("utf-8");
  let tampon = "";
  try {
    for (;;) {
      const { value, done } = await okuyucu.read();
      if (done) break;
      tampon += cozucu.decode(value, { stream: true });
      const { olaylar, kalan } = cerceveleriCoz(tampon);
      tampon = kalan;
      for (const olay of olaylar) olayIsle(olay);
    }
    tampon += cozucu.decode();
    if (tampon.trim()) {
      const { olaylar } = cerceveleriCoz(`${tampon}\n\n`);
      for (const olay of olaylar) olayIsle(olay);
    }
  } catch (hata) {
    await okuyucu.cancel().catch(() => undefined);
    throw hata;
  } finally {
    okuyucu.releaseLock();
  }
}
