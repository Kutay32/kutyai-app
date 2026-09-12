import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Koşullu sınıfları birleştirir, çakışan Tailwind sınıflarında sonuncuyu kazandırır. */
export function cn(...girdiler: ClassValue[]): string {
  return twMerge(clsx(girdiler));
}
