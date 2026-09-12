"use client";

import { useEffect, useState, type ReactNode } from "react";

import Link from "next/link";

import { istek } from "@/lib/api";
import { Brand } from "@/components/panel/brand";
import { Sidebar } from "@/components/panel/sidebar";
import { Topbar } from "@/components/panel/topbar";
import type { Kullanici, KurulumDurumu } from "@/lib/tipler";

export type PanelShellProps = {
  kullanici: Kullanici;
  children: ReactNode;
};

/** Panel kabuğu: sol menü, üst bar ve mobil çekmece. */
export function PanelShell({ kullanici, children }: PanelShellProps) {
  const [markaAdi, setMarkaAdi] = useState("KutyAI");
  const [cekimceAcik, setCekimceAcik] = useState(false);

  useEffect(() => {
    let iptal = false;
    istek<KurulumDurumu>("/saglik/kurulum", { jeton: null })
      .then((veri) => {
        if (!iptal && veri.marka_adi) setMarkaAdi(veri.marka_adi);
      })
      .catch(() => {
        // Marka adı alınamazsa varsayılan ad kullanılır.
      });
    return () => {
      iptal = true;
    };
  }, []);

  return (
    <div className="min-h-screen md:grid md:grid-cols-[16rem_1fr]">
      <aside className="hidden border-r border-neutral-200 bg-white md:flex md:h-screen md:flex-col md:sticky md:top-0">
        <div className="flex h-14 shrink-0 items-center border-b border-neutral-200 px-4">
          <Link
            href="/"
            className="rounded-md focus:outline-none focus:border-neutral-900 focus:ring-0"
          >
            <Brand markaAdi={markaAdi} />
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto">
          <Sidebar />
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <Topbar
          markaAdi={markaAdi}
          kullanici={kullanici}
          onMenuToggle={() => setCekimceAcik(true)}
        />
        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>

      {cekimceAcik ? (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <button
            type="button"
            aria-label="Menüyü kapat"
            onClick={() => setCekimceAcik(false)}
            className="absolute inset-0 cursor-default bg-neutral-900/40"
          />
          <div className="relative z-10 flex h-full w-72 flex-col border-r border-neutral-200 bg-white">
            <div className="flex h-14 shrink-0 items-center justify-between border-b border-neutral-200 px-4">
              <Brand markaAdi={markaAdi} />
              <button
                type="button"
                onClick={() => setCekimceAcik(false)}
                className="rounded-md px-3 py-1.5 text-sm text-neutral-600 transition-colors hover:bg-neutral-100 hover:text-neutral-900 focus:outline-none focus:border-neutral-900 focus:ring-0"
              >
                Kapat
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <Sidebar onNavigate={() => setCekimceAcik(false)} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
