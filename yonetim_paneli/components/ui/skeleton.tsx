import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

/** Yükleniyor yer tutucusu. */
export function Skeleton({ className, ...kalan }: ComponentProps<"div">) {
  return (
    <div
      aria-hidden
      className={cn("animate-pulse rounded-md bg-neutral-200", className)}
      {...kalan}
    />
  );
}
