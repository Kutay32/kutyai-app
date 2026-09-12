import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const TONE: Record<BadgeTone, string> = {
  neutral: "border-neutral-300 bg-neutral-100 text-neutral-700",
  success: "border-emerald-300 bg-emerald-50 text-emerald-700",
  warning: "border-amber-300 bg-amber-50 text-amber-800",
  danger: "border-rose-300 bg-rose-50 text-rose-700",
  info: "border-sky-300 bg-sky-50 text-sky-800",
};

export type BadgeProps = ComponentProps<"span"> & {
  tone?: BadgeTone;
};

export function Badge({ tone = "neutral", className, ...kalan }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium",
        TONE[tone],
        className,
      )}
      {...kalan}
    />
  );
}
