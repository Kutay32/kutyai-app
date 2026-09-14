/**
 * BDM (Bağlı Dil Modeli) veri katmanı — `kaynak/API.md` §8, §10, §11.
 *
 * Katalog uçları (`/bdm`), hazırlama (`/bdm/hazirlama`) ve yönetim
 * (`/bdm/yonetim`) uçlarının tamamı burada toplanır. İki uç SSE akıtır
 * (`/cek`, `/gunlukler`); `EventSource` özel başlık gönderemediği için
 * yetkilendirilmiş `fetch` + `ReadableStream` ile okunur.
 */

import { ApiHatasi, API_TABANI, istek } from "@/lib/api";
import { oturumOku } from "@/lib/oturum";
import { aktifDil, ceviri } from "@/lib/sozluk";
import type { Bdm, BdmDurumu, Saglayici, SaglayiciBilgisi, SurucuDurumu } from "@/lib/tipler";

/** `Bdm.konteyner` + §11 yönlendirme (`yol`) ve konteyner kimliği alanları. */
export type BdmKonteyner = {
  image?: string;
  gpu?: boolean;
  port?: number;
  bellek_gb?: number;
  konteyner_id?: string;
  yol?: { takma_ad?: string; oncelik?: number };
};

/** `konteyner` alanı yönlendirme bilgisiyle genişletilmiş BDM kaydı. */
export type BdmKaydi = Omit<Bdm, "konteyner"> & { konteyner: BdmKonteyner | null };

/** `POST /bdm` ve `PATCH /bdm/{id}` gövdesi (§8). */
export type BdmGirdisi = {
  gorunen_ad: string;
  slug?: string;
  aciklama: string;
  saglayici: Saglayici;
  temel_url: string;
  upstream_model: string;
  api_anahtari: string;
  baglam_penceresi: number;
  maks_cikti: number;
  sicaklik_varsayilan: number;
  sistem_istemi: string;
};

/** `POST /bdm/hazirlama/{id}/dogrula` yanıtı (§10). */
export type DogrulamaSonucu = {
  basarili: boolean;
  gecikme_ms: number;
  modeller: string[];
  mesaj: string;
};

/** `GET /bdm/hazirlama/{id}/on-kontrol` yanıtı (§10). */
export type OnKontrolSonucu = {
  docker: boolean;
  gpu: boolean;
  disk_gb: number;
  image_var: boolean;
  uygun: boolean;
  uyarilar: string[];
};

/** `POST /bdm/hazirlama/{id}/manifest` yanıtı (§10). */
export type Manifest = {
  image: string;
  komut: string[];
  port: number;
  gpu: boolean;
  bellek_gb: number;
  ortam: Record<string, string>;
  saglik_url?: string;
};

/** `POST /bdm/hazirlama/{id}/cek` akışındaki `ilerleme` olayı (§10). */
export type IlerlemeOlayi = { yuzde: number; mesaj: string };

/** `GET /bdm/yonetim/{id}/durum` yanıtı (§11). */
export type DurumYaniti = {
  durum: BdmDurumu;
  konteyner_id: string | null;
  saglik: { calisiyor: boolean; hazir: boolean; mesaj: string };
};

/** `GET /bdm/yonetim/{id}/saglik` yanıtı (§11). */
export type SaglikYaniti = {
  calisiyor: boolean;
  hazir: boolean;
  mesaj: string;
  ayrinti?: unknown;
};

/** `PATCH /bdm/yonetim/{id}/yol` gövdesi (§11). */
export type YonlendirmeGirdisi = { takma_ad?: string; oncelik?: number };

/** Arka uç yetenek matrisiyle aynı GPU gerektiren sağlayıcılar (§10). */
const GPU_GEREKEN: Record<string, true> = { vllm: true, tgi: true };

/** Sağlayıcı GPU gerektiriyor mu? */
export function gpuGerekir(saglayici: Saglayici): boolean {
  return GPU_GEREKEN[saglayici] === true;
}

/**
 * GPU gerektiren sağlayıcıda GPU yoksa gösterilecek gerekçe; sorun yoksa `null`.
 * Arka uç `503 surucu_yok` ile aynı gerekçeyi kullanır (§10).
 */
export function gpuEngeli(
  saglayici: Saglayici,
  surucu: SurucuDurumu | null | undefined,
): string | null {
  if (!gpuGerekir(saglayici) || !surucu || surucu.gpu) return null;
  return surucu.mesaj.trim() || ceviri("bdm.hata.gpu_yok", aktifDil());
}

/** Durum makinesine göre başlatma yapılabilir mi (§11). */
export function baslatilabilir(durum: BdmDurumu): boolean {
  return durum === "hazir" || durum === "durdu";
}

/** Durum makinesine göre durdurma yapılabilir mi (§11). */
export function durdurulabilir(durum: BdmDurumu): boolean {
  return durum === "calisiyor" || durum === "hata";
}

// ---------------------------------------------------------------- katalog (§8)

/** `GET /saglayicilar` — kimlik gerektirmez. */
export function saglayicilariGetir(): Promise<SaglayiciBilgisi[]> {
  return istek<SaglayiciBilgisi[]>("/saglayicilar", { jeton: null });
}

/** `GET /bdm?arama=` — personel yetkisi. */
export function bdmListesi(arama?: string): Promise<BdmKaydi[]> {
  const sorgu = arama?.trim() ? `?arama=${encodeURIComponent(arama.trim())}` : "";
  return istek<BdmKaydi[]>(`/bdm${sorgu}`);
}

/** `GET /bdm/{id}`; `GET /bdm` listesinden tek kayıt seçer. */
export async function bdmGetir(id: number): Promise<BdmKaydi> {
  const kayitlar = await bdmListesi();
  const bulunan = kayitlar.find((kayit) => kayit.id === id);
  if (!bulunan) throw new ApiHatasi(404, "bulunamadi", ceviri("bdm.hata.kayit_yok", aktifDil()));
  return bulunan;
}

/** `POST /bdm` — yönetici/operatör. */
export function bdmOlustur(girdi: BdmGirdisi): Promise<BdmKaydi> {
  return istek<BdmKaydi>("/bdm", { yontem: "POST", govde: girdi });
}

/** `PATCH /bdm/{id}` — yönetici/operatör. */
export function bdmGuncelle(id: number, girdi: Partial<BdmGirdisi>): Promise<BdmKaydi> {
  return istek<BdmKaydi>(`/bdm/${id}`, { yontem: "PATCH", govde: girdi });
}

/** `POST /bdm/{id}/kopyala` — yönetici. */
export function bdmKopyala(id: number, yeniAd: string, yeniSlug?: string): Promise<BdmKaydi> {
  return istek<BdmKaydi>(`/bdm/${id}/kopyala`, {
    yontem: "POST",
    govde: { yeni_ad: yeniAd, yeni_slug: yeniSlug?.trim() || null },
  });
}

/** `DELETE /bdm/{id}` — yönetici; bağlı kayıt varsa `409 gecersiz_gecis`. */
export function bdmSil(id: number): Promise<void> {
  return istek<void>(`/bdm/${id}`, { yontem: "DELETE" });
}

// -------------------------------------------------------------- hazırlama (§10)

/** `POST /bdm/hazirlama/{id}/dogrula`. */
export function hazirlamaDogrula(id: number): Promise<DogrulamaSonucu> {
  return istek<DogrulamaSonucu>(`/bdm/hazirlama/${id}/dogrula`, { yontem: "POST" });
}

/** `GET /bdm/hazirlama/{id}/on-kontrol`. */
export function hazirlamaOnKontrol(id: number): Promise<OnKontrolSonucu> {
  return istek<OnKontrolSonucu>(`/bdm/hazirlama/${id}/on-kontrol`);
}

/** `POST /bdm/hazirlama/{id}/manifest`; uzak sağlayıcıda `400 gecersiz_istek`. */
export function hazirlamaManifest(id: number): Promise<Manifest> {
  return istek<Manifest>(`/bdm/hazirlama/${id}/manifest`, { yontem: "POST" });
}

// ---------------------------------------------------------------- yönetim (§11)

/** `GET /bdm/yonetim/surucu/durum`. */
export function surucuDurumuGetir(): Promise<SurucuDurumu> {
  return istek<SurucuDurumu>("/bdm/yonetim/surucu/durum");
}

/** `POST /bdm/yonetim/{id}/baslat`; geçersiz geçişte `409 gecersiz_gecis`. */
export function bdmBaslat(id: number): Promise<{ durum: BdmDurumu; konteyner_id: string }> {
  return istek(`/bdm/yonetim/${id}/baslat`, { yontem: "POST" });
}

/** `POST /bdm/yonetim/{id}/durdur`. */
export function bdmDurdur(id: number): Promise<{ durum: BdmDurumu }> {
  return istek(`/bdm/yonetim/${id}/durdur`, { yontem: "POST" });
}

/** `POST /bdm/yonetim/{id}/yeniden-baslat`. */
export function bdmYenidenBaslat(
  id: number,
): Promise<{ durum: BdmDurumu; konteyner_id: string }> {
  return istek(`/bdm/yonetim/${id}/yeniden-baslat`, { yontem: "POST" });
}

/** `GET /bdm/yonetim/{id}/durum`. */
export function bdmDurumGetir(id: number): Promise<DurumYaniti> {
  return istek<DurumYaniti>(`/bdm/yonetim/${id}/durum`);
}

/** `GET /bdm/yonetim/{id}/saglik`. */
export function bdmSaglikGetir(id: number): Promise<SaglikYaniti> {
  return istek<SaglikYaniti>(`/bdm/yonetim/${id}/saglik`);
}

/** `PATCH /bdm/yonetim/{id}/yol` — takma ad ve öncelik. */
export function yonlendirmeGuncelle(
  id: number,
  girdi: YonlendirmeGirdisi,
): Promise<BdmKaydi> {
  return istek<BdmKaydi>(`/bdm/yonetim/${id}/yol`, { yontem: "PATCH", govde: girdi });
}

// ------------------------------------------------------------------ SSE akışı

type SseSecenekleri = { yontem?: "GET" | "POST"; sinyal?: AbortSignal };
type SseCercevesi = { olay: string; veri: unknown };

/** Hata zarfını SSE çerçevesinden ApiHatası'na çevirir (§1, §9). */
function akisHatasi(govde: unknown): ApiHatasi {
  const hata = (govde as { hata?: { kod?: unknown; mesaj?: unknown; ayrinti?: unknown } } | null)
    ?.hata;
  const kod = typeof hata?.kod === "string" ? hata.kod : "akis_hatasi";
  const mesaj =
    typeof hata?.mesaj === "string" && hata.mesaj.trim()
      ? hata.mesaj
      : ceviri("bdm.hata.akis", aktifDil());
  return new ApiHatasi(0, kod, mesaj, hata?.ayrinti);
}

/** Tek bir SSE çerçevesini çözer; yorum (`: nabız`) satırları yok sayılır. */
function cerceveyiCoz(ham: string): SseCercevesi | null {
  let olay = "mesaj";
  const veriSatirlari: string[] = [];
  for (const satir of ham.split(/\r?\n/)) {
    if (!satir || satir.startsWith(":")) continue;
    if (satir.startsWith("event:")) olay = satir.slice(6).trim();
    else if (satir.startsWith("data:")) veriSatirlari.push(satir.slice(5).trimStart());
  }
  if (veriSatirlari.length === 0) return null;
  const metin = veriSatirlari.join("\n");
  try {
    return { olay, veri: JSON.parse(metin) as unknown };
  } catch {
    return { olay, veri: { metin } };
  }
}

/** HTTP hata yanıtını aktif dilde mesajlı ApiHatası'na çevirir. */
async function akisYanitHatasi(cevap: Response): Promise<ApiHatasi> {
  let govde: unknown = null;
  try {
    govde = await cevap.json();
  } catch {
    govde = null;
  }
  if (govde === null) {
    return new ApiHatasi(
      cevap.status,
      "akis_hatasi",
      ceviri("bdm.hata.akis_baslatilamadi", aktifDil(), { durum: cevap.status }),
    );
  }
  const hata = akisHatasi(govde);
  return new ApiHatasi(cevap.status, hata.kod, hata.message, hata.ayrinti);
}

/**
 * Yetkilendirilmiş SSE akışını çerçeve çerçeve okur.
 * `event: hata` çerçevesi aktif dilde mesajlı `ApiHatasi` olarak fırlatılır (§1, §9).
 */
async function* sseAkisi(
  yol: string,
  secenekler: SseSecenekleri = {},
): AsyncGenerator<SseCercevesi> {
  const basliklar: Record<string, string> = { Accept: "text/event-stream" };
  const jeton = oturumOku("erisim");
  if (jeton) basliklar.Authorization = `Bearer ${jeton}`;

  let cevap: Response;
  try {
    cevap = await fetch(`${API_TABANI}${yol}`, {
      method: secenekler.yontem ?? "GET",
      headers: basliklar,
      cache: "no-store",
      signal: secenekler.sinyal,
    });
  } catch (hata) {
    if (hata instanceof Error && hata.name === "AbortError") throw hata;
    throw new ApiHatasi(0, "baglanti_hatasi", ceviri("api.baglanti_hatasi", aktifDil()));
  }

  if (!cevap.ok) throw await akisYanitHatasi(cevap);
  if (!cevap.body) {
    throw new ApiHatasi(0, "akis_yok", ceviri("bdm.hata.akis_govdesi", aktifDil()));
  }

  const okuyucu = cevap.body.getReader();
  const cozucu = new TextDecoder();
  let tampon = "";
  try {
    for (;;) {
      const { done, value } = await okuyucu.read();
      if (done) break;
      tampon += cozucu.decode(value, { stream: true });

      let ayrac = /\r?\n\r?\n/.exec(tampon);
      while (ayrac && ayrac.index !== undefined) {
        const ham = tampon.slice(0, ayrac.index);
        tampon = tampon.slice(ayrac.index + ayrac[0].length);
        const cerceve = cerceveyiCoz(ham);
        if (cerceve) {
          if (cerceve.olay === "hata") throw akisHatasi(cerceve.veri);
          yield cerceve;
        }
        ayrac = /\r?\n\r?\n/.exec(tampon);
      }
    }
  } finally {
    try {
      await okuyucu.cancel();
    } catch {
      // Akış zaten kapanmışsa iptal hatası yok sayılır.
    }
  }
}

/**
 * `POST /bdm/hazirlama/{id}/cek` — model indirme akışı.
 * `ilerleme` olayları sırayla üretilir; `bitti` olayında akış sonlanır.
 */
export async function* cekAkisi(
  id: number,
  sinyal?: AbortSignal,
): AsyncGenerator<IlerlemeOlayi> {
  for await (const cerceve of sseAkisi(`/bdm/hazirlama/${id}/cek`, { yontem: "POST", sinyal })) {
    if (cerceve.olay === "bitti") return;
    const veri = cerceve.veri as Partial<IlerlemeOlayi>;
    yield {
      yuzde: typeof veri.yuzde === "number" ? Math.max(0, Math.min(100, veri.yuzde)) : 0,
      mesaj: typeof veri.mesaj === "string" ? veri.mesaj : "",
    };
  }
}

/**
 * `GET /bdm/yonetim/{id}/gunlukler?satir=` — konteyner günlük akışı.
 * `satir` olaylarının `metin` alanı üretilir; nabız yorumları yok sayılır.
 */
export async function* gunlukAkisi(
  id: number,
  satir = 200,
  sinyal?: AbortSignal,
): AsyncGenerator<string> {
  for await (const cerceve of sseAkisi(
    `/bdm/yonetim/${id}/gunlukler?satir=${satir}`,
    { sinyal },
  )) {
    if (cerceve.olay !== "satir") continue;
    const veri = cerceve.veri as { metin?: unknown };
    if (typeof veri.metin === "string") yield veri.metin;
  }
}
