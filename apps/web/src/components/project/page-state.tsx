import type { ReactNode } from "react";

import { ButtonLink } from "@/components/ui/button";

/** A calm, actionable state for a record or source page: what happened and the way forward. */
export function PageState({
  actionHref,
  actionLabel,
  body,
  title
}: Readonly<{ actionHref: string; actionLabel: string; body: string; title: string }>): ReactNode {
  return (
    <div
      className="grid max-w-[68ch] gap-3 border border-border bg-card p-5"
      data-slot="page-state"
    >
      <h1 className="m-0 text-ledger-xl">{title}</h1>
      <p className="m-0">{body}</p>
      <div>
        <ButtonLink href={actionHref} variant="secondary">
          {actionLabel}
        </ButtonLink>
      </div>
    </div>
  );
}
