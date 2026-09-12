import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";
import { FIELD_CONTROL, FIELD_INVALID } from "@/components/ui/stiller";

export type TextareaProps = ComponentProps<"textarea"> & {
  /** Doğrulama hatası durumunda kenarlığı rose yapar. */
  invalid?: boolean;
};

export function Textarea({ className, invalid = false, rows = 4, ...kalan }: TextareaProps) {
  return (
    <textarea
      rows={rows}
      aria-invalid={invalid || undefined}
      className={cn(FIELD_CONTROL, "resize-y", invalid && FIELD_INVALID, className)}
      {...kalan}
    />
  );
}
