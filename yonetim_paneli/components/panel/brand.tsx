import { cn } from "@/lib/cn";

export type BrandProps = {
  markaAdi: string;
  className?: string;
};

/** Marka yazı markası; Instrument Serif yalnız burada kullanılır. */
export function Brand({ markaAdi, className }: BrandProps) {
  return (
    <span className={cn("font-serif text-xl leading-none tracking-tight text-neutral-900", className)}>
      {markaAdi}
    </span>
  );
}
