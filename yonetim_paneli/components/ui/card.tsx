import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

export type CardProps = ComponentProps<"div">;

/** Küçük kart yüzeyi. Büyük yüzeyler için `className="rounded-2xl"` geçin. */
export function Card({ className, ...kalan }: CardProps) {
  return (
    <div
      className={cn("rounded-lg border border-neutral-200 bg-white", className)}
      {...kalan}
    />
  );
}

export function CardHeader({ className, ...kalan }: ComponentProps<"div">) {
  return <div className={cn("flex flex-col gap-1 p-4", className)} {...kalan} />;
}

export function CardTitle({ className, ...kalan }: ComponentProps<"h2">) {
  return (
    <h2 className={cn("text-base font-semibold text-neutral-900", className)} {...kalan} />
  );
}

export function CardDescription({ className, ...kalan }: ComponentProps<"p">) {
  return <p className={cn("text-sm text-neutral-500", className)} {...kalan} />;
}

export function CardContent({ className, ...kalan }: ComponentProps<"div">) {
  return <div className={cn("p-4 pt-0", className)} {...kalan} />;
}

export function CardFooter({ className, ...kalan }: ComponentProps<"div">) {
  return (
    <div
      className={cn("flex items-center gap-2 border-t border-neutral-200 p-4", className)}
      {...kalan}
    />
  );
}
