import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";
import { FIELD_CONTROL, FIELD_INVALID } from "@/components/ui/stiller";

export type InputProps = ComponentProps<"input"> & {
  /** Doğrulama hatası durumunda kenarlığı rose yapar. */
  invalid?: boolean;
};

export function Input({ className, invalid = false, ...kalan }: InputProps) {
  return (
    <input
      aria-invalid={invalid || undefined}
      className={cn(FIELD_CONTROL, invalid && FIELD_INVALID, className)}
      {...kalan}
    />
  );
}
