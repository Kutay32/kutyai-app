import Link from "next/link";

import { cn } from "@/lib/cn";

/** Marka kilidi; serif yalnız marka adında kullanılır. */
export function Marka({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "marka-serif rounded-md text-2xl text-neutral-900 transition-colors hover:text-neutral-600 focus:border-neutral-900 focus:ring-0",
        className,
      )}
    >
      KutyAI
    </Link>
  );
}
