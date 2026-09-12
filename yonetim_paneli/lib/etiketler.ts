import type { BdmDurumu, KullaniciDurumu, Rol } from "@/lib/tipler";
import type { BadgeTone } from "@/components/ui/badge";

export const ROL_ETIKETI: Record<Rol, string> = {
  yonetici: "Yönetici",
  operator: "Operatör",
  izleyici: "İzleyici",
  son_kullanici: "Son Kullanıcı",
};

export const KULLANICI_DURUMU_ETIKETI: Record<KullaniciDurumu, string> = {
  aktif: "Aktif",
  beklemede: "Beklemede",
  pasif: "Pasif",
};

export const KULLANICI_DURUMU_TONU: Record<KullaniciDurumu, BadgeTone> = {
  aktif: "success",
  beklemede: "warning",
  pasif: "neutral",
};

export const BDM_DURUMU_ETIKETI: Record<BdmDurumu, string> = {
  taslak: "Taslak",
  hazir: "Hazır",
  calisiyor: "Çalışıyor",
  durdu: "Durdu",
  hata: "Hata",
};

export const BDM_DURUMU_TONU: Record<BdmDurumu, BadgeTone> = {
  taslak: "neutral",
  hazir: "info",
  calisiyor: "success",
  durdu: "warning",
  hata: "danger",
};
