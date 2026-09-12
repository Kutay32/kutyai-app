import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

export type LabelProps = ComponentProps<"label">;

export function Label({ className, children, ...kalan }: LabelProps) {
  return (
    <label className={cn("text-sm font-medium text-neutral-800", className)} {...kalan}>
      {children}
    </label>
  );
}
