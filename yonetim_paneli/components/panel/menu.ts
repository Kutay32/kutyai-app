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
   * Sayfası bu dalgada mevcut mu? `false` olan öğeler menüde gizlenir
   * (ör. sayfası henüz yazılmamış bir rota eklenirse).
   */
  hazir: boolean;
};

/** Sol menü sırası spec §12.2 ile aynıdır. */
export const MENU: MenuOgesi[] = [
  { href: "/", etiket: "Kontrol Paneli", ikon: LayoutDashboard, hazir: true },
  { href: "/bdm", etiket: "BDM'ler", ikon: Bot, hazir: true },
  { href: "/loglar", etiket: "Konuşma Kayıtları", ikon: MessagesSquare, hazir: true },
  { href: "/kullanim", etiket: "Kullanım", ikon: BarChart3, hazir: true },
  { href: "/kullanicilar", etiket: "Kullanıcılar", ikon: Users, hazir: true },
  { href: "/api-anahtarlari", etiket: "API Anahtarları", ikon: KeyRound, hazir: true },
  { href: "/ayarlar", etiket: "Ayarlar", ikon: Settings, hazir: true },
  { href: "/islem-kayitlari", etiket: "İşlem Kayıtları", ikon: ScrollText, hazir: true },
];

/** Yolu menüde gösterilecek (sayfası olan) öğelere indirger. */
export const GORUNUR_MENU = MENU.filter((oge) => oge.hazir);
