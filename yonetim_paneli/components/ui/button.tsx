import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";
import { Spinner } from "@/components/ui/spinner";
import { FOCUS_RING } from "@/components/ui/stiller";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    "border border-neutral-900 bg-neutral-900 text-white hover:bg-neutral-800 focus:border-neutral-400",
  secondary: "border border-neutral-300 bg-white text-neutral-900 hover:border-neutral-900",
  ghost: "border border-transparent bg-transparent text-neutral-700 hover:bg-neutral-100",
  danger:
    "border border-rose-600 bg-rose-600 text-white hover:bg-rose-700 focus:border-rose-300",
};

const SIZE: Record<ButtonSize, string> = {
  sm: "h-8 gap-1.5 px-3 text-sm",
  md: "h-10 gap-2 px-4 text-sm",
};

export type ButtonProps = ComponentProps<"button"> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** İstek sürerken true: düğme kilitlenir ve dönen gösterge çıkar. */
  loading?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  type = "button",
  ...kalan
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium whitespace-nowrap transition-colors disabled:pointer-events-none disabled:opacity-50",
        FOCUS_RING,
        VARIANT[variant],
        SIZE[size],
        className,
      )}
      {...kalan}
    >
      {loading ? <Spinner /> : null}
      {children}
    </button>
  );
}
