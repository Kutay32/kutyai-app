import type { ComponentProps, ReactNode } from "react";

import { CircleAlert, CircleCheck, Info, TriangleAlert } from "lucide-react";

import { cn } from "@/lib/cn";

export type AlertTone = "info" | "success" | "warning" | "danger";

const TONE: Record<AlertTone, { kutu: string; ikon: ReactNode }> = {
  info: { kutu: "border-sky-300 bg-sky-50 text-sky-900", ikon: <Info aria-hidden className="size-4" /> },
  success: {
    kutu: "border-emerald-300 bg-emerald-50 text-emerald-900",
    ikon: <CircleCheck aria-hidden className="size-4" />,
  },
  warning: {
    kutu: "border-amber-300 bg-amber-50 text-amber-900",
    ikon: <TriangleAlert aria-hidden className="size-4" />,
  },
  danger: {
    kutu: "border-rose-300 bg-rose-50 text-rose-900",
    ikon: <CircleAlert aria-hidden className="size-4" />,
  },
};

export type AlertProps = ComponentProps<"div"> & {
  tone?: AlertTone;
  title?: string;
};

export function Alert({ tone = "info", title, className, children, ...kalan }: AlertProps) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("flex gap-2 rounded-lg border p-4 text-sm", TONE[tone].kutu, className)}
      {...kalan}
    >
      <span className="mt-0.5 shrink-0">{TONE[tone].ikon}</span>
      <div className="flex flex-col gap-1">
        {title ? <p className="font-medium">{title}</p> : null}
        {children ? <div className="[&_a]:underline">{children}</div> : null}
      </div>
    </div>
  );
}
