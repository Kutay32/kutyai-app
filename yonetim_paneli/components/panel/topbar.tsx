"use client";

import { useState } from "react";

import { useRouter } from "next/navigation";

import { ChevronDown, LogOut, Menu, UserRound } from "lucide-react";

import { istek } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import { ROL_ANAHTARI } from "@/lib/etiketler";
import { oturumOku, oturumTemizle } from "@/lib/oturum";
import type { Kullanici } from "@/lib/tipler";
import { Brand } from "@/components/panel/brand";
import { DilSecici } from "@/components/panel/dil-secici";

export type TopbarProps = {
  markaAdi: string;
  kullanici: Kullanici;
  onMenuToggle: () => void;
};

/** Üst bar: mobil menü düğmesi, marka ve kullanıcı menüsü. */
export function Topbar({ markaAdi, kullanici, onMenuToggle }: TopbarProps) {
  const router = useRouter();
  const { t } = useDil();
  const [menuAcik, setMenuAcik] = useState(false);
  const [cikiliyor, setCikiliyor] = useState(false);

  const cikisYap = async () => {
    setCikiliyor(true);
    const yenileme = oturumOku("yenileme");
    try {
      await istek("/kimlik/cikis", {
        yontem: "POST",
        govde: yenileme ? { yenileme_jetonu: yenileme } : {},
        yenile: false,
      });
    } catch {
      // Sunucuya ulaşılamasa bile yerel oturum kapatılır.
    }
    oturumTemizle();
    router.replace("/giris");
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-neutral-200 bg-white px-4">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onMenuToggle}
          aria-label={t("genel.menu.ac")}
          className="rounded-md p-2 text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900 focus:outline-none focus:border-neutral-900 focus:ring-0 md:hidden"
        >
          <Menu aria-hidden className="size-5" />
        </button>
        <Brand markaAdi={markaAdi} className="md:hidden" />
      </div>

      <div className="flex items-center gap-3">
        <DilSecici />
        <div className="relative">
          <button
            type="button"
            onClick={() => setMenuAcik((acik) => !acik)}
            aria-haspopup="menu"
            aria-expanded={menuAcik}
            className="flex items-center gap-2 rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-800 transition-colors hover:border-neutral-900 focus:outline-none focus:border-neutral-900 focus:ring-0"
          >
            <UserRound aria-hidden className="size-4 text-neutral-500" />
            <span className="max-w-[12rem] truncate">{kullanici.ad_soyad}</span>
            <ChevronDown aria-hidden className="size-4 text-neutral-500" />
          </button>

          {menuAcik ? (
            <>
              <button
                type="button"
                aria-label={t("genel.menu.kapat")}
                onClick={() => setMenuAcik(false)}
                className="fixed inset-0 z-10 cursor-default"
              />
              <div
                role="menu"
                className="absolute right-0 z-20 mt-2 w-64 rounded-lg border border-neutral-200 bg-white p-1"
              >
                <div className="px-3 py-2">
                  <p className="truncate text-sm font-medium text-neutral-900">
                    {kullanici.ad_soyad}
                  </p>
                  <p className="truncate text-xs text-neutral-500">{kullanici.eposta}</p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {t(ROL_ANAHTARI[kullanici.rol])}
                  </p>
                </div>
                <div className="my-1 border-t border-neutral-200" />
                <button
                  type="button"
                  role="menuitem"
                  onClick={cikisYap}
                  disabled={cikiliyor}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-neutral-700 transition-colors hover:bg-neutral-100 focus:outline-none focus:border-neutral-900 focus:ring-0 disabled:opacity-50",
                  )}
                >
                  <LogOut aria-hidden className="size-4" />
                  {cikiliyor ? t("genel.cikis.yapiliyor") : t("genel.cikis")}
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
