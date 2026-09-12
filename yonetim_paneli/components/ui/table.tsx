import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

export function Table({ className, ...kalan }: ComponentProps<"table">) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn("w-full caption-bottom text-sm", className)} {...kalan} />
    </div>
  );
}

export function TableHeader({ className, ...kalan }: ComponentProps<"thead">) {
  return <thead className={cn("border-b border-neutral-200", className)} {...kalan} />;
}

export function TableBody({ className, ...kalan }: ComponentProps<"tbody">) {
  return <tbody className={cn("divide-y divide-neutral-100", className)} {...kalan} />;
}

export function TableRow({ className, ...kalan }: ComponentProps<"tr">) {
  return <tr className={cn("transition-colors hover:bg-neutral-50", className)} {...kalan} />;
}

export function TableHead({ className, ...kalan }: ComponentProps<"th">) {
  return (
    <th
      className={cn(
        "px-4 py-2.5 text-left text-xs font-medium tracking-wide text-neutral-500 uppercase",
        className,
      )}
      {...kalan}
    />
  );
}

export function TableCell({ className, ...kalan }: ComponentProps<"td">) {
  return <td className={cn("px-4 py-3 align-middle text-neutral-700", className)} {...kalan} />;
}
