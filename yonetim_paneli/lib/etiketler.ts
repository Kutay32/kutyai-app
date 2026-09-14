import type { SozlukAnahtari } from "@/lib/sozluk";
import type { BdmDurumu, KullaniciDurumu, Rol } from "@/lib/tipler";
import type { BadgeTone } from "@/components/ui/badge";

/** Etiketler katalogdan gelir (spec §10.2); bunlar yalnız anahtar eşlemesidir. */
export const ROL_ANAHTARI: Record<Rol, SozlukAnahtari> = {
  yonetici: "rol.yonetici",
  operator: "rol.operator",
  izleyici: "rol.izleyici",
  son_kullanici: "rol.son_kullanici",
};

export const KULLANICI_DURUMU_ANAHTARI: Record<KullaniciDurumu, SozlukAnahtari> = {
  aktif: "durum.aktif",
  beklemede: "durum.beklemede",
  pasif: "durum.pasif",
};

export const KULLANICI_DURUMU_TONU: Record<KullaniciDurumu, BadgeTone> = {
  aktif: "success",
  beklemede: "warning",
  pasif: "neutral",
};

export const BDM_DURUMU_ANAHTARI: Record<BdmDurumu, SozlukAnahtari> = {
  taslak: "durum.bdm.taslak",
  hazir: "durum.bdm.hazir",
  calisiyor: "durum.bdm.calisiyor",
  durdu: "durum.bdm.durdu",
  hata: "durum.bdm.hata",
};

export const BDM_DURUMU_TONU: Record<BdmDurumu, BadgeTone> = {
  taslak: "neutral",
  hazir: "info",
  calisiyor: "success",
  durdu: "warning",
  hata: "danger",
};
