"use client";

import { cn } from "@/lib/cn";

export type SwitchProps = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  /** Ekranda görünen etiket; verilirse denetime bağlanır. */
  label?: string;
  id?: string;
  className?: string;
};

export function Switch({
  checked,
  onChange,
  disabled = false,
  label,
  id,
  className,
}: SwitchProps) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative inline-flex h-5 w-9 shrink-0 items-center rounded-md border transition-colors focus:outline-none focus:border-neutral-900 focus:ring-0 disabled:cursor-not-allowed disabled:opacity-50",
          checked
            ? "border-neutral-900 bg-neutral-900 focus:border-neutral-400"
            : "border-neutral-300 bg-neutral-200",
        )}
      >
        <span
          aria-hidden
          className={cn(
            "size-4 rounded-sm bg-white transition-transform",
            checked ? "translate-x-4" : "translate-x-0.5",
          )}
        />
      </button>
      {label ? (
        <label htmlFor={id} className="text-sm text-neutral-800">
          {label}
        </label>
      ) : null}
    </span>
  );
}
