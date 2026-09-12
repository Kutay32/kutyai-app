"use client";

import { useId, type ReactNode } from "react";

import { cn } from "@/lib/cn";
import { Label } from "@/components/ui/label";

/** `Field` tarafından denetime aktarılan erişilebilirlik öznitelikleri. */
export type FieldControlProps = {
  id: string;
  invalid: boolean;
  "aria-describedby": string | undefined;
};

export type FieldProps = {
  label: string;
  /** Alanın altında görünen açıklama; hata varken gizlenir. */
  hint?: string;
  /** Türkçe doğrulama hatası; doluysa kenarlık rose olur. */
  error?: string | null;
  required?: boolean;
  className?: string;
  children: (props: FieldControlProps) => ReactNode;
};

/**
 * Etiket + denetim + ipucu/hata bağlar. Denetim, kimlik ve `aria-*`
 * özniteliklerini alan bir işlevle üretilir; böylece etiket–denetim
 * ilişkisi ve hata duyurusu otomatik doğru kurulur.
 */
export function Field({
  label,
  hint,
  error,
  required = false,
  className,
  children,
}: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-ipucu` : undefined;
  const errorId = error ? `${id}-hata` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <Label htmlFor={id}>
        {label}
        {required ? (
          <span aria-hidden className="ml-0.5 text-rose-600">
            *
          </span>
        ) : null}
      </Label>

      {children({ id, invalid: Boolean(error), "aria-describedby": describedBy })}

      {hint && !error ? (
        <p id={hintId} className="text-xs text-neutral-500">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-xs text-rose-600">
          {error}
        </p>
      ) : null}
    </div>
  );
}
