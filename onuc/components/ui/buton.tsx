"use client";

import { forwardRef } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/cn";

export type ButonTuru = "birincil" | "ikincil" | "hayalet" | "tehlike";
export type ButonBoyutu = "kucuk" | "orta" | "buyuk";

export type ButonOzellikleri = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  tur?: ButonTuru;
  boyut?: ButonBoyutu;
  /** İstek sürerken butonu kilitler ve dönen gösterge basar. */
  yukleniyor?: boolean;
};

const TUR_SINIFLARI: Record<ButonTuru, string> = {
  birincil: "border border-neutral-900 bg-neutral-900 text-white hover:bg-neutral-800",
  ikincil: "border border-neutral-200 bg-white text-neutral-900 hover:border-neutral-900",
  hayalet: "border border-transparent bg-transparent text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900",
  tehlike: "border border-rose-200 bg-white text-rose-600 hover:border-rose-600",
};

const BOYUT_SINIFLARI: Record<ButonBoyutu, string> = {
  kucuk: "h-8 px-3 text-[13px] gap-1.5",
  orta: "h-10 px-4 text-sm gap-2",
  buyuk: "h-11 px-5 text-sm gap-2",
};

export const Buton = forwardRef<HTMLButtonElement, ButonOzellikleri>(function Buton(
  { tur = "birincil", boyut = "orta", yukleniyor = false, className, children, disabled, type, ...kalan },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      aria-busy={yukleniyor || undefined}
      disabled={disabled || yukleniyor}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium transition-colors",
        "focus:border-neutral-900 focus:ring-0 focus-visible:border-neutral-900",
        "disabled:cursor-not-allowed disabled:opacity-50",
        TUR_SINIFLARI[tur],
        BOYUT_SINIFLARI[boyut],
        className,
      )}
      {...kalan}
    >
      {yukleniyor ? <Loader2 aria-hidden className="size-4 shrink-0 animate-spin" /> : null}
      {children}
    </button>
  );
});
