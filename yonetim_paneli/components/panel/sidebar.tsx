"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";
import { GORUNUR_MENU } from "@/components/panel/menu";

export type SidebarProps = {
  /** Mobil çekmecede bir öğeye tıklanınca çekmeceyi kapatır. */
  onNavigate?: () => void;
  className?: string;
};

function aktifMi(yol: string, href: string): boolean {
  return href === "/" ? yol === "/" : yol === href || yol.startsWith(`${href}/`);
}

/** Sol menü listesi; masaüstünde sabit sütun, mobilde çekmece içinde kullanılır. */
export function Sidebar({ onNavigate, className }: SidebarProps) {
  const yol = usePathname();

  return (
    <nav aria-label="Ana menü" className={cn("flex flex-col gap-1 p-4", className)}>
      {GORUNUR_MENU.map((oge) => {
        const aktif = aktifMi(yol, oge.href);
        const Ikon = oge.ikon;
        return (
          <Link
            key={oge.href}
            href={oge.href}
            onClick={onNavigate}
            aria-current={aktif ? "page" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-900 focus-visible:ring-offset-2",
              aktif
                ? "bg-neutral-900 font-medium text-white"
                : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900",
            )}
          >
            <Ikon aria-hidden className="size-4 shrink-0" />
            {oge.etiket}
          </Link>
        );
      })}
    </nav>
  );
}
