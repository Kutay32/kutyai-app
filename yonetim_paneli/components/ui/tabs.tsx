"use client";

import { cn } from "@/lib/cn";

export type TabItem = {
  value: string;
  label: string;
  count?: number;
};

export type TabsProps = {
  items: TabItem[];
  value: string;
  onValueChange: (value: string) => void;
  className?: string;
};

/** Kenarlık-odaklı, denetimli sekme çubuğu (içerik çağıran tarafından çizilir). */
export function Tabs({ items, value, onValueChange, className }: TabsProps) {
  return (
    <div
      role="tablist"
      className={cn("flex flex-wrap items-center gap-1 border-b border-neutral-200", className)}
    >
      {items.map((oge) => {
        const secili = oge.value === value;
        return (
          <button
            key={oge.value}
            type="button"
            role="tab"
            aria-selected={secili}
            onClick={() => onValueChange(oge.value)}
            className={cn(
              "-mb-px rounded-t-md border-b-2 px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:border-neutral-900 focus:ring-0",
              secili
                ? "border-neutral-900 text-neutral-900"
                : "border-transparent text-neutral-500 hover:text-neutral-900",
            )}
          >
            {oge.label}
            {typeof oge.count === "number" ? (
              <span className="ml-2 rounded-md bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600">
                {oge.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
