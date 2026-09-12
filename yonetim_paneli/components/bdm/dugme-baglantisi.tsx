import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { FOCUS_RING } from "@/components/ui/stiller";

/** Düğme görünümlü bağlantı; `Button` bir `button` ürettiği için gezinmede kullanılır. */
export type DugmeBaglantisiProps = {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
  className?: string;
};

const VARIANT = {
  primary:
    "border-neutral-900 bg-neutral-900 text-white hover:bg-neutral-800 focus:border-neutral-400",
  secondary: "border-neutral-300 bg-white text-neutral-900 hover:border-neutral-900",
} as const;

export function DugmeBaglantisi({
  href,
  children,
  variant = "primary",
  className,
}: DugmeBaglantisiProps) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex h-10 items-center justify-center gap-2 rounded-md border px-4 text-sm font-medium whitespace-nowrap transition-colors",
        FOCUS_RING,
        VARIANT[variant],
        className,
      )}
    >
      {children}
    </Link>
  );
}
