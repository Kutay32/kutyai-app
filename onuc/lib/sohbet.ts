/**
 * Sohbet uçları (API.md §9): model listesi, konuşma geçmişi ve SSE akışı.
 *
 * Akış `fetch` + `ReadableStream` ile okunur; çerçeve çözümlemesi saf fonksiyon
 * (`cerceveleriCoz`) olarak ayrıldığı için ağ olmadan sınanabilir.
 */

import { ApiHatasi, API_URL, apiFetch } from "./api";
import { oturumAl } from "./oturum";
import { aktifCeviri, tarayiciDili } from "./tarayici-dil";
import type { SozlukAnahtari } from "./sozluk";
import type { Kullanici } from "./tipler";

/** API.md §2 `BdmOzet` — `/modeller` yanıtının kaydı. */
export type BdmOzet = {
  id: number;
  slug: string;
  gorunen_ad: string;
  aciklama: string;
  saglayici: string;
  baglam_penceresi: number;
  yetenekler: { akis?: boolean; gorsel?: boolean; ses?: boolean; arac?: boolean };
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
  /** Sohbete eklenen dosyalar; metni çıkarılmış içerik sistem istemine eklenir (§3). */
  dosya_idleri?: number[];
  /** Bilgi tabanından parça ekleme anahtarı (§5). */
  rag?: boolean;
  /** Yalnız bu belgelerden arama; boş bırakılırsa tüm bilgi tabanı taranır. */
  rag_belge_idleri?: number[];
  /** Modele sunulacak araç slug'ları (§4). */
  arac_sluglari?: string[];
};

/** Asistana eklenen RAG parçası (`kaynaklar` satırı; API.md §20). */
export type SohbetKaynagi = {
  belge_id: number;
  belge_ad: string;
  /** Parçanın belge içindeki sırası. */
  sira: number;
  /** Kosinüs benzerliği (0–1). */
  skor: number;
};

/** Araç çağrısının sonucu (API.md §19). */
export type AracDurumu = "basarili" | "hata";

/** `/sohbet` yanıtı ve akışın `bitti` olayındaki araç özeti satırı. */
export type AracOzeti = { ad: string; durum: AracDurumu };

/** Araç kartının ekrandaki hâli: çağrı sürerken `calisiyor`. */
export type AracKarti = {
  ad: string;
  durum: AracDurumu | "calisiyor";
  /** Modelin ürettiği argümanlar; olayda taşınmazsa `null`. */
  argumanlar: unknown;
  /** Sonuç özeti; `arac_sonucu` olayı ya da `arac_cagrilari` doldurur. */
  ozet: string | null;
};

/** Araç durumu etiketleri katalogdan gelir (spec §10.2); bunlar anahtar eşlemesidir. */
export const ARAC_DURUM_ANAHTARLARI: Record<AracKarti["durum"], SozlukAnahtari> = {
  calisiyor: "sohbet.arac.durum.calisiyor",
  basarili: "sohbet.arac.durum.basarili",
  hata: "sohbet.arac.durum.hata",
};

/** `GET /araclar` satırının sohbette gereken alanları (API.md §19). */
export type AracSecenegi = {
  id: number;
  ad: string;
  slug: string;
  aciklama: string;
  etkin: boolean;
};

/** Etkin araçlar; sohbette `arac_sluglari` seçeneklerini üretir. */
export async function etkinAraclariGetir(): Promise<AracSecenegi[]> {
  return apiFetch<AracSecenegi[]>("/araclar?etkin=true");
}

/** `/sohbet` tek yanıt gövdesi (API.md §9); `kaynaklar` ve `arac_cagrilari` ek alanlarıdır. */
export type SohbetYaniti = {
  konusma_id: number;
  mesaj_id: number;
  icerik: string;
  token_girdi: number;
  token_cikti: number;
  gecikme_ms: number;
  kaynaklar?: SohbetKaynagi[];
  arac_cagrilari?: AracOzeti[];
};

/** Akışın `bitti` olayı, tek yanıtın özet alanlarını aynı adlarla taşır. */
export type SohbetOzeti = Pick<SohbetYaniti, "kaynaklar" | "arac_cagrilari">;

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
  /** Kullanıcı mesajıyla gönderilen dosyalar (yeniden üretimde aynen yinelenir). */
  dosya_idleri?: number[];
  /** Gönderilen dosyaların görünen adları. */
  dosya_adlari?: string[];
  /** Asistan yanıtında kullanılan RAG parçaları. */
  kaynaklar?: SohbetKaynagi[];
  /** Asistan yanıtının araç çağrıları (canlı olaylar + yanıt özeti). */
  araclar?: AracKarti[];
};

/** `/sohbet/akis` olayları (API.md §9, §19 SSE biçimi). */
export type SohbetOlayi =
  | { tur: "baslangic"; konusma_id: number; mesaj_id: number }
  | { tur: "parca"; icerik: string }
  | { tur: "kullanim"; token_girdi: number; token_cikti: number; gecikme_ms: number }
  | { tur: "arac_cagrisi"; ad: string; argumanlar: unknown }
  | { tur: "arac_sonucu"; ad: string; durum: AracDurumu; ozet: string }
  | { tur: "hata"; kod: string; mesaj: string; ayrinti: unknown }
  | ({ tur: "bitti" } & SohbetOzeti)
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

/* ---------------------------------------------------- dönüşümler */

function nesneler(ham: unknown): Record<string, unknown>[] {
  if (!Array.isArray(ham)) return [];
  return ham.filter(
    (satir): satir is Record<string, unknown> => typeof satir === "object" && satir !== null,
  );
}

/** `kaynaklar` alanını ekranda gösterilecek satırlara çevirir; bozuk satırlar atılır. */
export function kaynaklariCoz(ham: unknown): SohbetKaynagi[] {
  const sonuc: SohbetKaynagi[] = [];
  for (const satir of nesneler(ham)) {
    const belgeId = Number(satir.belge_id);
    if (!Number.isFinite(belgeId)) continue;
    sonuc.push({
      belge_id: belgeId,
      belge_ad: typeof satir.belge_ad === "string" ? satir.belge_ad : "",
      sira: Number(satir.sira) || 0,
      skor: Number(satir.skor) || 0,
    });
  }
  return sonuc;
}

/** `arac_cagrilari` alanını araç kartlarına çevirir; bilinmeyen durum "hata" sayılır. */
export function aracOzetleriniCoz(ham: unknown): AracOzeti[] {
  const sonuc: AracOzeti[] = [];
  for (const satir of nesneler(ham)) {
    const ad = satir.ad;
    if (typeof ad !== "string" || !ad) continue;
    sonuc.push({ ad, durum: aracDurumu(satir.durum) });
  }
  return sonuc;
}

function aracDurumu(ham: unknown): AracDurumu {
  return ham === "basarili" ? "basarili" : "hata";
}

/** `arac_cagrisi` olayını kart listesine ekler (`durum: "calisiyor"`). */
export function aracCagrisiEkle(kartlar: readonly AracKarti[], cagri: { ad: string; argumanlar: unknown }): AracKarti[] {
  return [...kartlar, { ad: cagri.ad, durum: "calisiyor", argumanlar: cagri.argumanlar, ozet: null }];
}

/**
 * Canlı kartları araç sonuçlarıyla (SSE `arac_sonucu`, akış `bitti` özeti)
 * birleştirir. Aynı adın n'inci sonucu, o adın n'inci kartını kapatır; eşleşen
 * kart yoksa yeni kart eklenir. Böylece `bitti` özeti kartları çiftlemez.
 */
export function aracKartlariniBirlestir(
  kartlar: readonly AracKarti[],
  sonuclar: readonly (AracOzeti & { ozet?: string | null })[],
): AracKarti[] {
  const sonuc = kartlar.map((kart) => ({ ...kart }));
  const sayac = new Map<string, number>();
  for (const ozet of sonuclar) {
    const kacinci = sayac.get(ozet.ad) ?? 0;
    sayac.set(ozet.ad, kacinci + 1);
    const siralar = sonuc.reduce<number[]>(
      (toplam, kart, sira) => (kart.ad === ozet.ad ? [...toplam, sira] : toplam),
      [],
    );
    const hedef = siralar[kacinci];
    if (hedef === undefined) {
      sonuc.push({ ad: ozet.ad, durum: ozet.durum, argumanlar: null, ozet: ozet.ozet ?? null });
      continue;
    }
    sonuc[hedef] = { ...sonuc[hedef], durum: ozet.durum, ozet: ozet.ozet ?? sonuc[hedef].ozet };
  }
  return sonuc;
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
      mesaj: typeof zarf.mesaj === "string" ? zarf.mesaj : aktifCeviri("sohbet.akis.uretim.hata"),
      ayrinti: zarf.ayrinti,
    };
  }
  if (ad === "arac_cagrisi") {
    const aracAdi = kayit.ad;
    if (typeof aracAdi !== "string" || !aracAdi) return { tur: "gecersiz", ad, ham };
    return { tur: "arac_cagrisi", ad: aracAdi, argumanlar: kayit.argumanlar ?? null };
  }
  if (ad === "arac_sonucu") {
    const aracAdi = kayit.ad;
    if (typeof aracAdi !== "string" || !aracAdi) return { tur: "gecersiz", ad, ham };
    return {
      tur: "arac_sonucu",
      ad: aracAdi,
      durum: aracDurumu(kayit.durum),
      ozet: typeof kayit.ozet === "string" ? kayit.ozet : "",
    };
  }
  if (ad === "bitti") {
    // `bitti` ek alanları yalnız doluysa taşınır; sade `{}` gövdesi `{ tur: "bitti" }` olur.
    const kaynaklar = kaynaklariCoz(kayit.kaynaklar);
    const aracCagrilari = aracOzetleriniCoz(kayit.arac_cagrilari);
    return {
      tur: "bitti",
      ...(kaynaklar.length > 0 ? { kaynaklar } : {}),
      ...(aracCagrilari.length > 0 ? { arac_cagrilari: aracCagrilari } : {}),
    };
  }
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
    hata?.mesaj ?? aktifCeviri("sohbet.akis.istek.hata"),
    hata?.ayrinti,
  );
}

async function akisIstegi(istek: SohbetAkisiIstegi, sinyal?: AbortSignal): Promise<Response> {
  const gonder = async (jeton: string | null): Promise<Response> => {
    const basliklar: Record<string, string> = {
      Accept: "text/event-stream",
      "Content-Type": "application/json",
      // Akıştaki hata zarfları ve HTTP hataları seçilen dilde dönsün (spec §10.1).
      "Accept-Language": tarayiciDili(),
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
      throw new ApiHatasi(0, "baglanti_hatasi", aktifCeviri("genel.hata.baglanti"));
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
    throw new ApiHatasi(yanit.status, "akis_yok", aktifCeviri("sohbet.akis.okunamadi"));
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
