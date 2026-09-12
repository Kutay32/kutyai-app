import type { ComponentProps } from "react";

import { LoaderCircle } from "lucide-react";

import { cn } from "@/lib/cn";

export type SpinnerProps = ComponentProps<"svg"> & {
  /** Erişilebilirlik metni; verilmezse görsel öğe ekran okuyuculardan gizlenir. */
  label?: string;
};

/** Yükleniyor göstergesi. */
export function Spinner({ className, label, ...kalan }: SpinnerProps) {
  return (
    <LoaderCircle
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? "status" : undefined}
      className={cn("size-4 shrink-0 animate-spin", className)}
      {...kalan}
    />
  );
}
