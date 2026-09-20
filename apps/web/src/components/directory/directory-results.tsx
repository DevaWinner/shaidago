import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { ButtonLink } from "@/components/ui/button";
import { formatMessage, type Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { Locality, ProjectPage, PublicRead } from "@/lib/api/public-data";
import { activeFilterNames, directoryHref, type DirectoryFilters } from "@/lib/directory/filters";
import type { Formatters } from "@/lib/format/formatters";
import { ProjectCard } from "@/components/directory/project-card";

function StateMessage({
  action,
  body,
  title
}: Readonly<{ action: ReactNode; body: string; title: string }>): ReactNode {
  return (
    <div
      className="grid max-w-[68ch] gap-3 border border-border bg-card p-5"
      data-slot="directory-state"
    >
      <h3 className="m-0 text-ledger-lg">{title}</h3>
      <p className="m-0">{body}</p>
      {action}
    </div>
  );
}

/**
 * The results region and every state it can be in: results, first-load empty, no matches, an
 * invalid cursor, and an unavailable service. Each state keeps the filters and the way forward.
 */
export function DirectoryResults({
  copy,
  evidence,
  filters,
  format,
  language,
  locale,
  localities,
  now,
  read
}: Readonly<{
  copy: Messages["directory"];
  evidence: Messages["evidence"];
  filters: DirectoryFilters;
  format: Formatters;
  language: ApiLocale;
  locale: string;
  localities: readonly Locality[];
  now: Date;
  read: PublicRead<ProjectPage>;
}>): ReactNode {
  const states = copy.states;
  const here = directoryHref(locale, filters, { cursor: true, withResults: true });
  const firstPage = directoryHref(locale, filters, { withResults: true });

  let body: ReactNode;
  let announcement = "";

  if (read.state === "unavailable") {
    body = (
      <StateMessage
        action={
          <ButtonLink href={here} variant="secondary">
            {states.unavailable.retry}
          </ButtonLink>
        }
        body={states.unavailable.body}
        title={states.unavailable.title}
      />
    );
  } else if (read.state === "invalid_cursor") {
    body = (
      <StateMessage
        action={
          <ButtonLink href={firstPage} variant="secondary">
            {states.invalidCursor.first}
          </ButtonLink>
        }
        body={states.invalidCursor.body}
        title={states.invalidCursor.title}
      />
    );
  } else if (read.data.items.length === 0) {
    const filtered = activeFilterNames(filters).length > 0;
    const message = filtered ? states.noMatches : states.empty;

    announcement = message.title;
    body = (
      <StateMessage
        action={
          filtered ? (
            <ButtonLink href={directoryHref(locale, {}, { withResults: true })} variant="secondary">
              {copy.form.clear}
            </ButtonLink>
          ) : null
        }
        body={message.body}
        title={message.title}
      />
    );
  } else {
    const { items, nextCursor } = read.data;
    const usesOriginal = items.some((item) => item.text.is_fallback);
    const machineAssisted = items.some(
      (item) => item.text.translation_status === "machine_assisted"
    );

    announcement = formatMessage(language, copy.results.shown, { count: items.length });
    body = (
      <>
        {usesOriginal ? (
          <TranslationNotice labels={evidence.translation} status="unavailable" />
        ) : machineAssisted ? (
          <TranslationNotice labels={evidence.translation} status="machine_assisted" />
        ) : null}
        <ol className="m-0 grid list-none p-0">
          {items.map((project, index) => (
            <li key={project.slug}>
              <ProjectCard
                copy={copy}
                format={format}
                headingId={`project-${index}`}
                language={language}
                locale={locale}
                locality={localities.find((item) => item.slug === project.locality_slug)}
                now={now}
                project={project}
              />
            </li>
          ))}
        </ol>
        {nextCursor !== null || filters.cursor !== undefined ? (
          <nav aria-label={copy.pagination.label} className="flex flex-wrap gap-3 pt-4">
            {filters.cursor === undefined ? null : (
              <ButtonLink href={firstPage} rel="first" variant="secondary">
                {copy.pagination.first}
              </ButtonLink>
            )}
            {nextCursor === null ? null : (
              <ButtonLink
                href={directoryHref(
                  locale,
                  { ...filters, cursor: nextCursor },
                  { cursor: true, withResults: true }
                )}
                rel="next"
                variant="secondary"
              >
                {copy.pagination.next}
              </ButtonLink>
            )}
          </nav>
        ) : null}
        {nextCursor !== null ? (
          <p className="m-0 text-sm text-muted-foreground">{copy.results.moreAvailable}</p>
        ) : null}
      </>
    );
  }

  return (
    <section
      aria-labelledby="results-heading"
      className="grid gap-4 focus:outline-none"
      data-slot="directory-results"
      id="results"
      tabIndex={-1}
    >
      <h2 className="m-0 text-ledger-xl" id="results-heading">
        {copy.results.heading}
      </h2>
      {/* One short, polite line: the count or the empty message. Not the whole list. */}
      <p aria-live="polite" className="m-0 text-sm text-muted-foreground" role="status">
        {announcement}
      </p>
      {body}
    </section>
  );
}
