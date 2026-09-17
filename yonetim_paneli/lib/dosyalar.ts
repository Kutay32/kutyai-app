/** `kaynak/API.md` §18 dosya istemcisi. */

import { aktifOrganizasyonOku } from "@/lib/aktif-organizasyon";
import { API_TABANI, ApiHatasi, dosyaIndir, istek } from "@/lib/api";
import { aktifDil, ceviri } from "@/lib/sozluk";
import { oturumOku } from "@/lib/oturum";
import type { Kullanici, Sayfa } from "@/lib/tipler";

export const VARSAYILAN_DOSYA_SAYFA_BOYUTU = 25;
export const DOSYA_SAYFA_BOYUTLARI = [25, 50, 100] as const;

/** `GET /dosyalar` satırı (`olusturulma` ve `metin_uzunluk` meta alanlarıdır). */
export type DosyaOzeti = {
  id: number;
  ad: string;
  mime: string;
  boyut: number;
  sha256: string;
  metin_uzunluk: number;
  kullanici_id: number | null;
  /** Sunucu boş bırakabilir; biçimleyici `—` gösterir. */
  olusturulma: string | null;
};

/** `GET /dosyalar/{id}`: meta + maskelenmiş çıkarılmış metin. */
export type DosyaDetayi = DosyaOzeti & { metin: string };

export type DosyaFiltresi = {
  arama: string;
  sayfa: number;
  boyut: number;
};

export const BASLANGIC_DOSYA_FILTRESI: DosyaFiltresi = {
  arama: "",
  sayfa: 1,
  boyut: VARSAYILAN_DOSYA_SAYFA_BOYUTU,
};

/** Dolu filtre alanlarından sorgu dizesi üretir (`arama` boşsa gönderilmez). */
export function dosyaSorgusu(filtre: DosyaFiltresi): string {
  const parametreler = new URLSearchParams();
  const arama = filtre.arama.trim();
  if (arama) parametreler.set("arama", arama);
  parametreler.set("sayfa", String(filtre.sayfa));
  parametreler.set("boyut", String(filtre.boyut));
  return parametreler.toString();
}

/** Aktif organizasyonun dosyaları (en yeni önce). */
export async function dosyalariGetir(filtre: DosyaFiltresi): Promise<Sayfa<DosyaOzeti>> {
  return istek<Sayfa<DosyaOzeti>>(`/dosyalar?${dosyaSorgusu(filtre)}`);
}

/** Dosya metası ve maskelenmiş metni; başka organizasyonun kaydı `404` verir. */
export async function dosyaDetayiGetir(dosyaId: number): Promise<DosyaDetayi> {
  return istek<DosyaDetayi>(`/dosyalar/${dosyaId}`);
}

/** Kaydı ve diskteki kopyayı siler. */
export async function dosyaSil(dosyaId: number): Promise<void> {
  await istek<void>(`/dosyalar/${dosyaId}`, { yontem: "DELETE" });
}

/** Ham içeriği `Content-Disposition` ile indirir (jeton yenilemeyi `api.ts` yürütür). */
export async function dosyaIcerikIndir(dosya: DosyaOzeti): Promise<void> {
  await dosyaIndir(`/dosyalar/${dosya.id}/icerik`, dosya.ad);
}

/**
 * Hata zarfını (`{ hata: { kod, mesaj, ayrinti } }`) istemci hatasına çevirir.
 *
 * `lib/api.ts` içindeki çözümleyici dışa açık değildir; multipart yolun aynı
 * sözleşmeyi taşıması için asgari bir kopyası burada tutulur.
 */
function zarfCoz(govde: unknown, durum: number): ApiHatasi {
  const hata = (govde as { hata?: { kod?: unknown; mesaj?: unknown; ayrinti?: unknown } } | null)
    ?.hata;
  const kod = typeof hata?.kod === "string" ? hata.kod : "bilinmeyen_hata";
  const mesaj =
    typeof hata?.mesaj === "string" && hata.mesaj.trim()
      ? hata.mesaj
      : ceviri("api.istek_tamamlanamadi", aktifDil());
  return new ApiHatasi(durum, kod, mesaj, hata?.ayrinti);
}

async function yanitCoz<T>(cevap: Response): Promise<T> {
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

/**
 * Multipart gövde gönderir.
 *
 * `lib/api.ts` gövdeyi her zaman JSON olarak serileştirdiği için (`Content-Type`
 * ve `JSON.stringify`) dosya yüklemesi burada kendi küçük yardımcısıyla taşınır;
 * jeton, `X-Organizasyon` ve `Accept-Language` başlıkları aynı kurallarla eklenir.
 * `401` alınırsa `GET /kimlik/ben` ile `api.ts`'in tekilleştirilmiş yenilemesi
 * tetiklenir ve istek güncel jetonla bir kez yinelenir.
 */
async function multipartGonder<T>(yol: string, govde: FormData, yenile = true): Promise<T> {
  const basliklar: Record<string, string> = { "Accept-Language": aktifDil() };
  const jeton = oturumOku("erisim");
  if (jeton) basliklar.Authorization = `Bearer ${jeton}`;
  const organizasyon = aktifOrganizasyonOku();
  if (organizasyon) basliklar["X-Organizasyon"] = organizasyon;

  let cevap: Response;
  try {
    cevap = await fetch(`${API_TABANI}${yol}`, {
      method: "POST",
      headers: basliklar,
      body: govde,
      cache: "no-store",
    });
  } catch {
    throw new ApiHatasi(0, "baglanti_hatasi", ceviri("api.baglanti_hatasi", aktifDil()));
  }

  if (cevap.status === 401 && yenile) {
    // Bu arada başka bir istek jetonu tazelediyse yenilemeye gerek yok: doğrudan
    // güncel jetonla denir (`api.ts` ile aynı davranış).
    const guncel = oturumOku("erisim");
    if (guncel && guncel !== jeton) {
      return multipartGonder<T>(yol, govde, false);
    }
    // Jeton bayat: `api.ts` yenilemeyi tekilleştirir ve yeni jetonu kaydeder.
    await istek<Kullanici>("/kimlik/ben");
    return multipartGonder<T>(yol, govde, false);
  }

  return yanitCoz<T>(cevap);
}

/** Multipart dosya yükler; sunucu MIME ve boyut denetimini uygular. */
export async function dosyaYukle(dosya: File): Promise<DosyaDetayi> {
  const govde = new FormData();
  govde.append("dosya", dosya);
  return multipartGonder<DosyaDetayi>("/dosyalar", govde);
}

const BOYUT_BIRIMLERI = ["B", "KB", "MB", "GB", "TB"] as const;

/** Baytı okunur biçime çevirir (ör. `1,2 MB`). */
export function boyutBicimle(bayt: number | null | undefined): string {
  if (typeof bayt !== "number" || !Number.isFinite(bayt)) return "—";
  let deger = Math.max(0, bayt);
  let indeks = 0;
  while (deger >= 1024 && indeks < BOYUT_BIRIMLERI.length - 1) {
    deger /= 1024;
    indeks += 1;
  }
  const bicimli = new Intl.NumberFormat(aktifDil(), {
    maximumFractionDigits: indeks === 0 ? 0 : 1,
  }).format(deger);
  return `${bicimli} ${BOYUT_BIRIMLERI[indeks]}`;
}
