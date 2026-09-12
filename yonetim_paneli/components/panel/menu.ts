import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bot,
  LayoutDashboard,
  KeyRound,
  MessagesSquare,
  ScrollText,
  Settings,
  Users,
} from "lucide-react";

export type MenuOgesi = {
  href: string;
  etiket: string;
  ikon: LucideIcon;
  /**
   * Sayfası bu dalgada mevcut mu? `false` olan öğeler menüde gizlenir;
   * Dalga 2'de ilgili sayfa yazıldığında `true` yapılır.
   */
  hazir: boolean;
};

/** Sol menü sırası spec §12.2 ile aynıdır. */
export const MENU: MenuOgesi[] = [
  { href: "/", etiket: "Kontrol Paneli", ikon: LayoutDashboard, hazir: true },
  { href: "/bdm", etiket: "BDM'ler", ikon: Bot, hazir: false },
  { href: "/loglar", etiket: "Konuşma Kayıtları", ikon: MessagesSquare, hazir: false },
  { href: "/kullanim", etiket: "Kullanım", ikon: BarChart3, hazir: false },
  { href: "/kullanicilar", etiket: "Kullanıcılar", ikon: Users, hazir: false },
  { href: "/api-anahtarlari", etiket: "API Anahtarları", ikon: KeyRound, hazir: false },
  { href: "/ayarlar", etiket: "Ayarlar", ikon: Settings, hazir: false },
  { href: "/islem-kayitlari", etiket: "İşlem Kayıtları", ikon: ScrollText, hazir: false },
];

/** Yolu menüde gösterilecek (sayfası olan) öğelere indirger. */
export const GORUNUR_MENU = MENU.filter((oge) => oge.hazir);
