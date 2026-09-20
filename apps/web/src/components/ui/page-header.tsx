import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** A consistent entry point for task pages. The icon is decorative; the heading remains the name. */
export function PageHeader({
  actions,
  className,
  icon: Icon,
  intro,
  title
}: Readonly<{
  actions?: ReactNode;
  className?: string;
  icon: LucideIcon;
  intro?: ReactNode;
  title: ReactNode;
}>): ReactNode {
  return (
    <header
      className={cn(
        "grid gap-4 border-b border-border pb-6 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-start",
        className
      )}
      data-slot="page-header"
    >
      <span className="grid size-11 place-items-center rounded-ledger-control bg-primary text-primary-foreground">
        <Icon aria-hidden="true" className="size-6" strokeWidth={1.7} />
      </span>
      <div className="grid min-w-0 gap-3">
        <h1 className="m-0 max-w-[24ch] text-ledger-display leading-[1.05] tracking-[-0.035em] [overflow-wrap:anywhere]">
          {title}
        </h1>
        {intro === undefined ? null : (
          <div className="max-w-[68ch] text-lg text-muted-foreground [&_p]:m-0">{intro}</div>
        )}
        {actions === undefined ? null : <div className="flex flex-wrap gap-3">{actions}</div>}
      </div>
    </header>
  );
}
