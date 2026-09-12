"use client";

import { forwardRef } from "react";

import { cn } from "@/lib/cn";

export type KartOzellikleri = React.HTMLAttributes<HTMLDivElement>;

export const Kart = forwardRef<HTMLDivElement, KartOzellikleri>(function Kart(
  { className, ...kalan },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn("rounded-lg border border-neutral-200 bg-white p-4", className)}
      {...kalan}
    />
  );
});

export type BuyukKartOzellikleri = React.HTMLAttributes<HTMLDivElement>;

/** Sayfa gövdesindeki büyük yüzeyler için yumuşak köşeli kart. */
export const BuyukKart = forwardRef<HTMLDivElement, BuyukKartOzellikleri>(function BuyukKart(
  { className, ...kalan },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn("rounded-2xl border border-neutral-200 bg-white p-4 md:p-6", className)}
      {...kalan}
    />
  );
});

export type KartBasligiOzellikleri = React.HTMLAttributes<HTMLHeadingElement> & {
  aciklama?: string;
};

export const KartBasligi = forwardRef<HTMLHeadingElement, KartBasligiOzellikleri>(
  function KartBasligi({ aciklama, className, children, ...kalan }, ref) {
    return (
      <div className="flex flex-col gap-1">
        <h2 ref={ref} className={cn("text-lg font-medium text-neutral-900", className)} {...kalan}>
          {children}
        </h2>
        {aciklama ? <p className="text-sm text-neutral-500">{aciklama}</p> : null}
      </div>
    );
  },
);

export const KartIcerigi = forwardRef<HTMLDivElement, KartOzellikleri>(function KartIcerigi(
  { className, ...kalan },
  ref,
) {
  return <div ref={ref} className={cn("text-sm text-neutral-600", className)} {...kalan} />;
});

export const KartAltbilgisi = forwardRef<HTMLDivElement, KartOzellikleri>(function KartAltbilgisi(
  { className, ...kalan },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn("mt-4 border-t border-neutral-100 pt-4 text-sm text-neutral-500", className)}
      {...kalan}
    />
  );
});
