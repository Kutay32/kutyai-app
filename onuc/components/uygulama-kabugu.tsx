"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { Marka } from "@/components/marka";
import { Buton } from "@/components/ui/buton";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useDil } from "@/lib/dil";
import { oturumAl, temizle } from "@/lib/oturum";
import type { SozlukAnahtari } from "@/lib/sozluk";
import { ROL_ANAHTARLARI, type Kullanici } from "@/lib/tipler";

const BAGLANTILAR: { yol: string; anahtar: SozlukAnahtari }[] = [
  { yol: "/sohbet", anahtar: "kabuk.baglanti.sohbet" },
  { yol: "/kullanim", anahtar: "kabuk.baglanti.kullanim" },
  { yol: "/hesap", anahtar: "kabuk.baglanti.hesap" },
];

export type UygulamaKabuguOzellikleri = {
  kullanici: Kullanici | null;
  children: React.ReactNode;
  /** Sohbet gibi tam yükseklikte çalışan sayfalar için kaydırmayı gövdeye bırakır. */
  tamYukseklik?: boolean;
};

export function UygulamaKabugu({
  kullanici,
  children,
  tamYukseklik = false,
}: UygulamaKabuguOzellikleri) {
  const yol = usePathname();
  const yonlendirici = useRouter();
  const { t } = useDil();
  const [cikiliyor, setCikiliyor] = useState(false);

  async function cikisYap() {
    setCikiliyor(true);
    const oturum = oturumAl();
    try {
      await apiFetch<{ mesaj: string }>("/kimlik/cikis", {
        method: "POST",
        govde: oturum ? { yenileme_jetonu: oturum.yenileme_jetonu } : {},
        yenilemeDene: false,
      });
    } catch {
      // Sunucu tarafı çıkış başarısız olsa da yerel oturum kapatılır.
    }
    temizle();
    yonlendirici.replace("/giris");
  }

  return (
    <div className={cn("flex min-h-dvh flex-col bg-white", tamYukseklik && "h-dvh")}>
      <header className="sticky top-0 z-40 border-b border-neutral-100 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 p-4">
          <div className="flex items-center gap-4">
            <Marka className="text-xl" />
            <nav aria-label={t("kabuk.menu")} className="flex items-center gap-1">
              {BAGLANTILAR.map((baglanti) => {
                const etkin = yol === baglanti.yol || yol.startsWith(`${baglanti.yol}/`);
                return (
                  <Link
                    key={baglanti.yol}
                    href={baglanti.yol}
                    aria-current={etkin ? "page" : undefined}
                    className={cn(
                      "rounded-md border px-3 py-1.5 text-[13px] transition-colors focus:border-neutral-900 focus:ring-0",
                      etkin
                        ? "border-neutral-900 text-neutral-900"
                        : "border-transparent text-neutral-500 hover:text-neutral-900",
                    )}
                  >
                    {t(baglanti.anahtar)}
                  </Link>
                );
              })}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-right md:block">
              <p className="text-[13px] font-medium text-neutral-900">
                {kullanici?.ad_soyad ?? t("kabuk.oturum")}
              </p>
              <p className="text-xs text-neutral-500">
                {kullanici ? t(ROL_ANAHTARLARI[kullanici.rol]) : t("kabuk.bilinmiyor")}
              </p>
            </div>
            <Buton tur="ikincil" boyut="kucuk" yukleniyor={cikiliyor} onClick={cikisYap}>
              {cikiliyor ? null : <LogOut aria-hidden className="size-3.5" />}
              {t("kabuk.cikis")}
            </Buton>
          </div>
        </div>
      </header>
      <main className={cn("flex-1", tamYukseklik && "min-h-0 overflow-hidden")}>{children}</main>
    </div>
  );
}
