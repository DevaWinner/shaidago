import type { ReactNode } from "react";

import type { Messages } from "@/i18n/catalogue";
import type { Locality } from "@/lib/api/public-data";
import {
  activeFilterNames,
  directoryHref,
  withoutFilter,
  type DirectoryFilters,
  type FilterName
} from "@/lib/directory/filters";
import { formatMessageLite } from "@/lib/directory/format-lite";

/**
 * Removable filter chips. Each is a plain link to the same results without that filter (and without
 * a cursor), so removing one works by keyboard and with no JavaScript, and lands on the results.
 * "Clear all" is one link. Nothing here reads or writes client state.
 */
export function FilterPills({
  copy,
  evidence,
  filters,
  localities,
  locale
}: Readonly<{
  copy: Messages["directory"];
  evidence: Messages["evidence"];
  filters: DirectoryFilters;
  localities: readonly Locality[];
  locale: string;
}>): ReactNode {
  const names = activeFilterNames(filters);

  if (names.length === 0) {
    return null;
  }

  const describe = (name: FilterName): string => {
    switch (name) {
      case "q":
        return formatMessageLite(copy.pills.search, { value: filters.q ?? "" });
      case "locality":
        return (
          localities.find((item) => item.slug === filters.locality)?.name ?? filters.locality ?? ""
        );
      case "category":
        return filters.category === undefined ? "" : copy.categories[filters.category];
      case "status":
        return filters.status === undefined ? "" : copy.statuses[filters.status];
      case "verification":
        return filters.verification === undefined
          ? ""
          : evidence.verification[filters.verification];
    }
  };

  return (
    <nav aria-label={copy.pills.label} data-slot="filter-pills">
      <ul className="m-0 flex list-none flex-wrap items-center gap-2 p-0">
        {names.map((name) => (
          <li key={name}>
            <a
              aria-label={formatMessageLite(copy.pills.remove, { filter: describe(name) })}
              className="inline-flex min-h-11 items-center gap-2 rounded-ledger-control border border-foreground bg-card px-3 py-1 text-sm font-semibold text-foreground no-underline [overflow-wrap:anywhere]"
              href={directoryHref(locale, withoutFilter(filters, name), { withResults: true })}
            >
              <span>{describe(name)}</span>
              <span aria-hidden="true">×</span>
            </a>
          </li>
        ))}
        <li>
          <a
            className="inline-flex min-h-11 items-center px-2 font-semibold text-ledger-accent-strong underline"
            href={directoryHref(locale, {}, { withResults: true })}
          >
            {copy.form.clear}
          </a>
        </li>
      </ul>
    </nav>
  );
}
