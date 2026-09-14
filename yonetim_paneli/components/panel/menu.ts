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

/** Sol menü sırası spec §12.2 ile aynıdır. */
export const MENU: MenuOgesi[] = [
  { href: "/", anahtar: "menu.kontrol", ikon: LayoutDashboard, hazir: true },
  { href: "/bdm", anahtar: "menu.bdm", ikon: Bot, hazir: true },
  { href: "/loglar", anahtar: "menu.loglar", ikon: MessagesSquare, hazir: true },
  { href: "/kullanim", anahtar: "menu.kullanim", ikon: BarChart3, hazir: true },
  { href: "/kullanicilar", anahtar: "menu.kullanicilar", ikon: Users, hazir: true },
  { href: "/api-anahtarlari", anahtar: "menu.anahtarlar", ikon: KeyRound, hazir: true },
  { href: "/ayarlar", anahtar: "menu.ayarlar", ikon: Settings, hazir: true },
  { href: "/islem-kayitlari", anahtar: "menu.islem", ikon: ScrollText, hazir: true },
];

/** Yolu menüde gösterilecek (sayfası olan) öğelere indirger. */
export const GORUNUR_MENU = MENU.filter((oge) => oge.hazir);
