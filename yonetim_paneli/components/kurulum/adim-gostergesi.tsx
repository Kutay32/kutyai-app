import { Check } from "lucide-react";

import { cn } from "@/lib/cn";

export type AdimGostergesiProps = {
  adimlar: string[];
  /** Sıfır tabanlı etkin adım indeksi. */
  aktif: number;
  className?: string;
};

/** Kurulum sihirbazının adım göstergesi. */
export function AdimGostergesi({ adimlar, aktif, className }: AdimGostergesiProps) {
  return (
    <ol className={cn("flex flex-wrap items-center gap-2", className)}>
      {adimlar.map((baslik, sira) => {
        const tamamlandi = sira < aktif;
        const secili = sira === aktif;
        return (
          <li key={baslik} className="flex items-center gap-2">
            {sira > 0 ? <span aria-hidden className="h-px w-6 bg-neutral-300" /> : null}
            <span
              aria-current={secili ? "step" : undefined}
              className={cn(
                "flex size-6 shrink-0 items-center justify-center rounded-md border text-xs font-medium",
                tamamlandi && "border-neutral-900 bg-neutral-900 text-white",
                secili && "border-neutral-900 text-neutral-900",
                !tamamlandi && !secili && "border-neutral-300 text-neutral-400",
              )}
            >
              {tamamlandi ? <Check aria-hidden className="size-3.5" /> : sira + 1}
            </span>
            <span
              className={cn(
                "text-sm",
                secili ? "font-medium text-neutral-900" : "text-neutral-500",
              )}
            >
              {baslik}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
