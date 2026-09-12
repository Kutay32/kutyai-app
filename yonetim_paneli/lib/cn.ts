import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Koşullu sınıfları birleştirir ve çakışan Tailwind sınıflarını sadeleştirir. */
export function cn(...girdiler: ClassValue[]): string {
  return twMerge(clsx(girdiler));
}
