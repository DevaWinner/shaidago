import type { ReactNode } from "react";

import { ButtonLink } from "@/components/ui/button";

/**
 * Cursor lists have no page count, so this offers previous/next links only. The URL owns the
 * state, which keeps filters shareable and the control usable without JavaScript.
 */
export function Pagination({
  label,
  next,
  previous
}: Readonly<{
  label: string;
  next?: Readonly<{ href: string; label: string }>;
  previous?: Readonly<{ href: string; label: string }>;
}>): ReactNode {
  return (
    <nav aria-label={label} className="flex flex-wrap gap-3" data-slot="pagination">
      {previous === undefined ? null : (
        <ButtonLink href={previous.href} rel="prev" variant="secondary">
          {previous.label}
        </ButtonLink>
      )}
      {next === undefined ? null : (
        <ButtonLink href={next.href} rel="next" variant="secondary">
          {next.label}
        </ButtonLink>
      )}
    </nav>
  );
}
