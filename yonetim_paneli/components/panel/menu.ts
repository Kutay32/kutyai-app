import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bot,
  Building2,
  CreditCard,
  FolderOpen,
  KeyRound,
  LayoutDashboard,
  Library,
  Mail,
  MessagesSquare,
  ScrollText,
  Settings,
  ShieldCheck,
  Users,
  Wrench,
} from "lucide-react";

import type { SozlukAnahtari } from "@/lib/sozluk";

export type MenuOgesi = {
  href: string;
  /** Menü etiketinin katalog anahtarı (spec §10.2). */
  anahtar: SozlukAnahtari;
  ikon: LucideIcon;
  /**
   * Sayfası bu dalgada mevcut mu? `false` olan öğeler menüde gizlenir
   * (ör. sayfası henüz yazılmamış bir rota eklenirse).
   */
  hazir: boolean;
};

/**
 * Sol menü sırası: v1 spec §12.2 çekirdeği korunur, v2 yetenekleri
 * (organizasyon, dosya, bilgi tabanı, araç, faturalama, posta, SSO) araya eklenir.
 */
export const MENU: MenuOgesi[] = [
  { href: "/", anahtar: "menu.kontrol", ikon: LayoutDashboard, hazir: true },
  { href: "/bdm", anahtar: "menu.bdm", ikon: Bot, hazir: true },
  { href: "/loglar", anahtar: "menu.loglar", ikon: MessagesSquare, hazir: true },
  { href: "/kullanim", anahtar: "menu.kullanim", ikon: BarChart3, hazir: true },
  { href: "/kullanicilar", anahtar: "menu.kullanicilar", ikon: Users, hazir: true },
  { href: "/organizasyonlar", anahtar: "menu.organizasyonlar", ikon: Building2, hazir: true },
  { href: "/dosyalar", anahtar: "menu.dosyalar", ikon: FolderOpen, hazir: true },
  { href: "/bilgi-tabani", anahtar: "menu.bilgi", ikon: Library, hazir: true },
  { href: "/araclar", anahtar: "menu.araclar", ikon: Wrench, hazir: true },
  { href: "/api-anahtarlari", anahtar: "menu.anahtarlar", ikon: KeyRound, hazir: true },
  { href: "/faturalama", anahtar: "menu.faturalama", ikon: CreditCard, hazir: true },
  { href: "/posta-sablonlari", anahtar: "menu.posta", ikon: Mail, hazir: true },
  { href: "/sso", anahtar: "menu.sso", ikon: ShieldCheck, hazir: true },
  { href: "/ayarlar", anahtar: "menu.ayarlar", ikon: Settings, hazir: true },
  { href: "/islem-kayitlari", anahtar: "menu.islem", ikon: ScrollText, hazir: true },
];

/** Yolu menüde gösterilecek (sayfası olan) öğelere indirger. */
export const GORUNUR_MENU = MENU.filter((oge) => oge.hazir);
