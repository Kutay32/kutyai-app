import type { ComponentProps } from "react";

import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/cn";
import { FIELD_CONTROL, FIELD_INVALID } from "@/components/ui/stiller";

export type SelectProps = ComponentProps<"select"> & {
  /** Doğrulama hatası durumunda kenarlığı rose yapar. */
  invalid?: boolean;
};

export function Select({ className, invalid = false, children, ...kalan }: SelectProps) {
  return (
    <div className="relative">
      <select
        aria-invalid={invalid || undefined}
        className={cn(FIELD_CONTROL, "appearance-none pr-9", invalid && FIELD_INVALID, className)}
        {...kalan}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-neutral-400"
      />
    </div>
  );
}
