/** `kaynak/API.md` §15 faturalama uçları istemcisi (spec §6). */

import { ApiHatasi, hataMesaji, istek } from "@/lib/api";
import { aktifDil, ceviri, type SozlukAnahtari } from "@/lib/sozluk";
import type { Sayfa } from "@/lib/tipler";
import type { BadgeTone } from "@/components/ui/badge";

export type AbonelikDurumu = "deneme" | "aktif" | "gecikmis" | "iptal";
export type FaturaDurumu = "taslak" | "odendi" | "basarisiz" | "iade";

export const VARSAYILAN_FATURA_SAYFA_BOYUTU = 25;
export const FATURA_SAYFA_BOYUTLARI = [25, 50, 100] as const;

/** Abone olurken sunulan dönem uzunlukları (gün). */
export const ABONELIK_DONEMLERI = [30, 90, 365] as const;

/** `GET /faturalama/planlar` satırı; fiyat metni sunucuda biçimlenir. */
export type Plan = {
  id: number;
  ad: string;
  slug: string;
  aylik_fiyat_kurus: number;
  /** Ör. `TRY 990,00`. */
  aylik_fiyat: string;
  para: string;
  dahil_istek: number | null;
  dahil_token: number | null;
  ozellikler: Record<string, unknown>;
  etkin: boolean;
};

/** `GET /faturalama/abonelik` yanıtı; kayıt yoksa `null`. */
export type Abonelik = {
  id: number;
  durum: AbonelikDurumu;
  plan: Plan | null;
  donem_basi: string;
  donem_sonu: string;
  saglayici: string;
  dis_id: string;
  /** `gecikmis` ve `iptal` dışında true (sunucu hesaplar). */
  erisim: boolean;
};

export type FaturaKalemi = {
  aciklama: string;
  tutar_kurus: number;
};

/** `GET /faturalama/faturalar` kaydı. */
export type Fatura = {
  id: number;
  tutar_kurus: number;
  /** Ör. `TRY 990,00`. */
  tutar: string;
  para: string;
  durum: FaturaDurumu;
  kalemler: FaturaKalemi[];
  dis_id: string;
  olusturulma: string;
  odeme_tarihi: string | null;
};

/** `POST /faturalama/abonelik` yanıtı. */
export type AbonelikSonucu = {
  abonelik: Abonelik | null;
  fatura: Fatura;
  /** `yerel` sağlayıcıda `null`. */
  odeme_url: string | null;
};

/** `POST /faturalama/odeme-oturumu` yanıtı (`OdemeSaglayici.odeme_oturumu`). */
export type OdemeOturumu = {
  dis_id?: string;
  url?: string | null;
  saglayici?: string;
};

export type AbonelikIstegi = { plan_id: number; donem_gun: number };

export const ABONELIK_DURUMU_ANAHTARI: Record<AbonelikDurumu, SozlukAnahtari> = {
  deneme: "faturalama.abonelik.durum.deneme",
  aktif: "faturalama.abonelik.durum.aktif",
  gecikmis: "faturalama.abonelik.durum.gecikmis",
  iptal: "faturalama.abonelik.durum.iptal",
};

export const ABONELIK_DURUMU_TONU: Record<AbonelikDurumu, BadgeTone> = {
  deneme: "info",
  aktif: "success",
  gecikmis: "danger",
  iptal: "neutral",
};

export const FATURA_DURUMU_ANAHTARI: Record<FaturaDurumu, SozlukAnahtari> = {
  taslak: "faturalama.fatura.durum.taslak",
  odendi: "faturalama.fatura.durum.odendi",
  basarisiz: "faturalama.fatura.durum.basarisiz",
  iade: "faturalama.fatura.durum.iade",
};

export const FATURA_DURUMU_TONU: Record<FaturaDurumu, BadgeTone> = {
  taslak: "warning",
  odendi: "success",
  basarisiz: "danger",
  iade: "neutral",
};

export function planlariGetir(): Promise<Plan[]> {
  return istek<Plan[]>("/faturalama/planlar");
}

export function abonelikGetir(): Promise<Abonelik | null> {
  return istek<Abonelik | null>("/faturalama/abonelik");
}

export function abonelikBaslat(girdi: AbonelikIstegi): Promise<AbonelikSonucu> {
  return istek<AbonelikSonucu>("/faturalama/abonelik", { yontem: "POST", govde: girdi });
}

export function abonelikIptal(): Promise<Abonelik> {
  return istek<Abonelik>("/faturalama/abonelik/iptal", { yontem: "POST" });
}

export function faturalariGetir(sayfa: number, boyut: number): Promise<Sayfa<Fatura>> {
  const parametreler = new URLSearchParams({
    sayfa: String(sayfa),
    boyut: String(boyut),
  });
  return istek<Sayfa<Fatura>>(`/faturalama/faturalar?${parametreler.toString()}`);
}

/** Yalnız `yerel` sağlayıcıda çalışır; başka sağlayıcıda sunucu 400 döner. */
export function faturaOdendi(faturaId: number): Promise<Fatura> {
  return istek<Fatura>(`/faturalama/faturalar/${faturaId}/odendi`, { yontem: "POST" });
}

export function odemeOturumuOlustur(faturaId: number): Promise<OdemeOturumu> {
  return istek<OdemeOturumu>("/faturalama/odeme-oturumu", {
    yontem: "POST",
    govde: { fatura_id: faturaId },
  });
}

/** Elle tahsilat yalnız yerel sağlayıcıda mümkündür (arkauc `fatura_odendi`). */
export function elleTahsilatYapilabilirMi(saglayici: string | undefined): boolean {
  return !saglayici || saglayici === "yerel";
}

const HATA_ANAHTARLARI: Record<string, SozlukAnahtari> = {
  plan_bulunamadi: "faturalama.hata.plan_bulunamadi",
  abonelik_yok: "faturalama.hata.abonelik_yok",
  odeme_saglayici_yok: "faturalama.hata.odeme_saglayici_yok",
  yetki_yok: "faturalama.hata.yetki_yok",
  org_erisim_yok: "faturalama.hata.yetki_yok",
};

/** Faturalama hata kodlarını aktif dilde anlaşılır metne çevirir. */
export function faturalamaHatasi(hata: unknown): string {
  if (hata instanceof ApiHatasi) {
    const anahtar = HATA_ANAHTARLARI[hata.kod];
    if (anahtar) return ceviri(anahtar, aktifDil());
  }
  return hataMesaji(hata);
}
