import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";
import { Card } from "@/components/ui/card";

export type StatCardProps = ComponentProps<"div"> & {
  label: string;
  value: string;
  hint?: string;
};

/** Tek bir ölçüyü gösteren küçük kart. */
export function StatCard({ label, value, hint, className, ...kalan }: StatCardProps) {
  return (
    <Card className={cn("flex flex-col gap-1 p-4", className)} {...kalan}>
      <p className="text-xs font-medium tracking-wide text-neutral-500 uppercase">{label}</p>
      <p className="text-2xl font-semibold tracking-tight text-neutral-900">{value}</p>
      {hint ? <p className="text-xs text-neutral-500">{hint}</p> : null}
    </Card>
  );
}
