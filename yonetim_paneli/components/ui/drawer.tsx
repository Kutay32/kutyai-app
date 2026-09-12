"use client";

import { useEffect, type ReactNode } from "react";

import { X } from "lucide-react";

import { cn } from "@/lib/cn";

export type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: ReactNode;
  footer?: ReactNode;
  className?: string;
};

/** Sağdan açılan çekmece; ESC ve arka plan tıklamasıyla kapanır. */
export function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  className,
}: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    const tusla = (olay: KeyboardEvent) => {
      if (olay.key === "Escape") onClose();
    };
    document.addEventListener("keydown", tusla);
    const tasma = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", tusla);
      document.body.style.overflow = tasma;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Kapat"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-neutral-900/40"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "relative z-10 flex h-full w-full max-w-md flex-col border-l border-neutral-200 bg-white",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-neutral-200 p-4">
          <div className="flex flex-col gap-1">
            <h2 className="text-base font-semibold text-neutral-900">{title}</h2>
            {description ? <p className="text-sm text-neutral-500">{description}</p> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Kapat"
            className="rounded-md p-1 text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-900 focus:outline-none focus:border-neutral-900 focus:ring-0"
          >
            <X aria-hidden className="size-4" />
          </button>
        </div>

        {children ? <div className="flex-1 overflow-y-auto p-4">{children}</div> : null}

        {footer ? (
          <div className="flex items-center justify-end gap-2 border-t border-neutral-200 p-4">
            {footer}
          </div>
        ) : null}
      </aside>
    </div>
  );
}
