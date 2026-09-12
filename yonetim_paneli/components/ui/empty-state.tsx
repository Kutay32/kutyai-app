import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-neutral-300 p-8 text-center",
        className,
      )}
    >
      {icon ? <span className="text-neutral-400">{icon}</span> : null}
      <p className="text-sm font-medium text-neutral-900">{title}</p>
      {description ? <p className="max-w-sm text-sm text-neutral-500">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
