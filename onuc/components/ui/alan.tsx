"use client";

import { forwardRef, useId } from "react";

import { cn } from "@/lib/cn";

export type AlanOzellikleri = React.InputHTMLAttributes<HTMLInputElement> & {
  etiket: string;
  /** Alan altındaki doğrulama hatası; `role="alert"` ile duyurulur. */
  hata?: string;
  /** Alan altındaki açıklama (hata yokken görünür). */
  yardim?: string;
};

export const Alan = forwardRef<HTMLInputElement, AlanOzellikleri>(function Alan(
  { etiket, hata, yardim, className, id, required, ...kalan },
  ref,
) {
  const uretilenId = useId();
  const alanId = id ?? `alan-${uretilenId}`;
  const hataId = `${alanId}-hata`;
  const yardimId = `${alanId}-yardim`;
  const aciklamaId = hata ? hataId : yardim ? yardimId : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={alanId} className="text-[13px] font-medium text-neutral-900">
        {etiket}
        {required ? <span className="ml-0.5 text-rose-600">*</span> : null}
      </label>
      <input
        ref={ref}
        id={alanId}
        required={required}
        aria-invalid={hata ? true : undefined}
        aria-describedby={aciklamaId}
        className={cn(
          "h-10 w-full rounded-lg border border-neutral-200 bg-white px-3 text-sm text-neutral-900 transition-colors",
          "placeholder:text-neutral-400",
          "focus:border-neutral-900 focus:ring-0 focus:outline-none",
          "disabled:cursor-not-allowed disabled:bg-neutral-50 disabled:text-neutral-500",
          hata && "border-rose-300 focus:border-rose-600",
          className,
        )}
        {...kalan}
      />
      {hata ? (
        <p id={hataId} role="alert" className="text-[13px] text-rose-600">
          {hata}
        </p>
      ) : yardim ? (
        <p id={yardimId} className="text-[13px] text-neutral-500">
          {yardim}
        </p>
      ) : null}
    </div>
  );
});
