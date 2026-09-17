import type { SozlukAnahtari } from "@/lib/sozluk";
import type {
  BdmDurumu,
  KullaniciDurumu,
  OrganizasyonDurumu,
  Rol,
  UyelikRolu,
} from "@/lib/tipler";
import type { BadgeTone } from "@/components/ui/badge";

/** Etiketler katalogdan gelir (spec §10.2); bunlar yalnız anahtar eşlemesidir. */
export const ROL_ANAHTARI: Record<Rol, SozlukAnahtari> = {
  yonetici: "rol.yonetici",
  operator: "rol.operator",
  izleyici: "rol.izleyici",
  son_kullanici: "rol.son_kullanici",
};

/** Organizasyon üyeliği rolleri (`sahip` yalnız üyelikte bulunur, spec §15). */
export const UYELIK_ROL_ANAHTARI: Record<UyelikRolu, SozlukAnahtari> = {
  sahip: "uyelik.sahip",
  yonetici: "uyelik.yonetici",
  operator: "uyelik.operator",
  izleyici: "uyelik.izleyici",
  son_kullanici: "uyelik.son_kullanici",
};

export const ORGANIZASYON_DURUMU_ANAHTARI: Record<OrganizasyonDurumu, SozlukAnahtari> = {
  aktif: "durum.org.aktif",
  askida: "durum.org.askida",
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
