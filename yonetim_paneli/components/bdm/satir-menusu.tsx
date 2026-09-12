"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import Link from "next/link";
import { Copy, MoreHorizontal, Pencil, Play, Square, Trash2 } from "lucide-react";

import { cn } from "@/lib/cn";
import { baslatilabilir, durdurulabilir, type BdmKaydi } from "@/lib/bdm";
import { FOCUS_RING } from "@/components/ui/stiller";

export type SatirMenusuProps = {
  bdm: BdmKaydi;
  /** Silme ve kopyalama yalnız yöneticide (API.md §8). */
  yonetici: boolean;
  /** GPU gerektiren sağlayıcıda GPU yoksa başlatmayı engelleyen Türkçe gerekçe. */
  gpuGerekcesi: string | null;
  islemde: boolean;
  onKopyala: () => void;
  onDurum: (eylem: "baslat" | "durdur") => void;
  onSil: () => void;
};

type OgeProps = {
  children: ReactNode;
  ikon: ReactNode;
  gerekce?: string | null;
  onClick?: () => void;
  href?: string;
};

function MenuOgesi({ children, ikon, gerekce, onClick, href }: OgeProps) {
  const sinif = cn(
    "flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm text-neutral-700 transition-colors",
    "focus:outline-none focus:border-neutral-900 focus:ring-0",
    gerekce
      ? "cursor-not-allowed opacity-50"
      : "hover:bg-neutral-100 hover:text-neutral-900",
  );

  const icerik = (
    <>
      <span className="mt-0.5 shrink-0">{ikon}</span>
      <span className="flex flex-col gap-0.5">
        <span>{children}</span>
        {gerekce ? <span className="text-xs text-neutral-500">{gerekce}</span> : null}
      </span>
    </>
  );

  if (href && !gerekce) {
    return (
      <Link href={href} role="menuitem" className={sinif} onClick={onClick}>
        {icerik}
      </Link>
    );
  }

  return (
    <button
      type="button"
      role="menuitem"
      aria-disabled={gerekce ? true : undefined}
      disabled={Boolean(gerekce)}
      title={gerekce ?? undefined}
      onClick={gerekce ? undefined : onClick}
      className={sinif}
    >
      {icerik}
    </button>
  );
}

/** BDM satır işlemleri: Düzenle, Kopyala, Çalıştır/Durdur, Sil. */
export function SatirMenusu({
  bdm,
  yonetici,
  gpuGerekcesi,
  islemde,
  onKopyala,
  onDurum,
  onSil,
}: SatirMenusuProps) {
  const [acik, setAcik] = useState(false);
  const kap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!acik) return;
    const disari = (olay: MouseEvent) => {
      if (kap.current && !kap.current.contains(olay.target as Node)) setAcik(false);
    };
    const tusla = (olay: KeyboardEvent) => {
      if (olay.key === "Escape") setAcik(false);
    };
    document.addEventListener("mousedown", disari);
    document.addEventListener("keydown", tusla);
    return () => {
      document.removeEventListener("mousedown", disari);
      document.removeEventListener("keydown", tusla);
    };
  }, [acik]);

  const calisiyor = bdm.durum === "calisiyor";
  const baslatGerekcesi =
    gpuGerekcesi ??
    (calisiyor
      ? "Bu model zaten çalışıyor."
      : baslatilabilir(bdm.durum)
        ? null
        : bdm.durum === "taslak"
          ? "Önce Hazırlama sekmesinden bağlantıyı doğrulayın."
          : "Hata durumundaki model önce durdurulmalıdır.");
  const durdurGerekcesi = durdurulabilir(bdm.durum) ? null : "Bu model çalışmıyor.";
  const kopyalaGerekcesi = yonetici ? null : "Kopyalama yalnız yönetici rolünde yapılabilir.";
  const silGerekcesi = !yonetici
    ? "Silme yalnız yönetici rolünde yapılabilir."
    : calisiyor
      ? "Çalışan model silinemez; önce durdurun."
      : null;

  return (
    <div ref={kap} className="relative inline-flex justify-end">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={acik}
        aria-label={`${bdm.gorunen_ad} işlemleri`}
        disabled={islemde}
        onClick={() => setAcik((onceki) => !onceki)}
        className={cn(
          "inline-flex size-8 items-center justify-center rounded-md border border-transparent text-neutral-500 transition-colors hover:border-neutral-300 hover:text-neutral-900 disabled:opacity-50",
          FOCUS_RING,
        )}
      >
        <MoreHorizontal aria-hidden className="size-4" />
      </button>

      {acik ? (
        <div
          role="menu"
          aria-label={`${bdm.gorunen_ad} işlemleri`}
          className="absolute top-9 right-0 z-20 flex w-64 flex-col gap-0.5 rounded-lg border border-neutral-200 bg-white p-1"
        >
          <MenuOgesi
            ikon={<Pencil aria-hidden className="size-4" />}
            href={`/bdm/${bdm.id}`}
            onClick={() => setAcik(false)}
          >
            Düzenle
          </MenuOgesi>

          <MenuOgesi
            ikon={<Copy aria-hidden className="size-4" />}
            gerekce={kopyalaGerekcesi}
            onClick={() => {
              setAcik(false);
              onKopyala();
            }}
          >
            Kopyala
          </MenuOgesi>

          {calisiyor || bdm.durum === "hata" ? (
            <MenuOgesi
              ikon={<Square aria-hidden className="size-4" />}
              gerekce={durdurGerekcesi}
              onClick={() => {
                setAcik(false);
                onDurum("durdur");
              }}
            >
              Durdur
            </MenuOgesi>
          ) : (
            <MenuOgesi
              ikon={<Play aria-hidden className="size-4" />}
              gerekce={baslatGerekcesi}
              onClick={() => {
                setAcik(false);
                onDurum("baslat");
              }}
            >
              Çalıştır
            </MenuOgesi>
          )}

          <MenuOgesi
            ikon={<Trash2 aria-hidden className="size-4" />}
            gerekce={silGerekcesi}
            onClick={() => {
              setAcik(false);
              onSil();
            }}
          >
            Sil
          </MenuOgesi>
        </div>
      ) : null}
    </div>
  );
}
