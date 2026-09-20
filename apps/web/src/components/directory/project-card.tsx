import type { ReactNode } from "react";

import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { Locality, ProjectSummary } from "@/lib/api/public-data";
import { formatMessage } from "@/i18n/catalogue";
import { STALE_AFTER_DAYS, isStale } from "@/lib/directory/freshness";
import type { Formatters } from "@/lib/format/formatters";

/**
 * One result. The title is the single, clearly named action; the facts under it are a definition
 * list, not a row of equal chips. The recorded status is what the record says, worded and styled
 * neutrally so it is never mistaken for verification. Text is shown in the language the API served
 * it in, with that language declared.
 */
export function ProjectCard({
  copy,
  format,
  headingId,
  language,
  locale,
  locality,
  now,
  project
}: Readonly<{
  copy: Messages["directory"];
  format: Formatters;
  headingId: string;
  /** The language the catalogue copy is written in, for plural rules. */
  language: ApiLocale;
  locale: string;
  locality: Locality | undefined;
  now: Date;
  project: ProjectSummary;
}>): ReactNode {
  const stale = isStale(project.last_checked_on, now);

  return (
    <article
      aria-labelledby={headingId}
      className="grid gap-2 border-b border-border py-5"
      data-slot="project-card"
    >
      <h2
        className="m-0 text-ledger-lg leading-tight"
        id={headingId}
        lang={project.text.served_locale}
      >
        <a
          className="text-foreground underline underline-offset-4"
          href={`/${locale}/projects/${encodeURIComponent(project.slug)}`}
        >
          {project.text.title}
        </a>
      </h2>
      <p className="m-0 max-w-[68ch] text-muted-foreground" lang={project.text.served_locale}>
        {project.text.summary}
      </p>
      <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(min(100%,11rem),1fr))] gap-x-6 gap-y-1 text-sm [&_dd]:m-0 [&_dd]:font-semibold [&_dt]:text-muted-foreground">
        <div>
          <dt>{copy.form.locality}</dt>
          <dd>{locality?.name ?? project.locality_slug}</dd>
        </div>
        <div>
          <dt>{copy.form.category}</dt>
          <dd>{copy.categories[project.category]}</dd>
        </div>
        <div>
          <dt>{copy.card.recordedStatus}</dt>
          <dd>{copy.statuses[project.public_status]}</dd>
        </div>
        <div>
          <dt>{copy.card.lastChecked}</dt>
          <dd>
            {project.last_checked_on === null ? (
              copy.card.notChecked
            ) : (
              <time dateTime={project.last_checked_on}>{format.date(project.last_checked_on)}</time>
            )}
          </dd>
        </div>
      </dl>
      {stale ? (
        <p className="m-0 text-sm text-ledger-warning">
          {formatMessage(language, copy.card.staleNote, { days: STALE_AFTER_DAYS })}
        </p>
      ) : null}
    </article>
  );
}
