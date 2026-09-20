import type { ReactNode } from "react";

import { InformationClassMarker } from "@/components/evidence/evidence";
import type { Messages } from "@/i18n/catalogue";
import type { SourceExcerpts } from "@/lib/api/public-data";
import type { Formatters } from "@/lib/format/formatters";

const LONG = 420;

function Passage({ full, label }: Readonly<{ full: string; label: string }>): ReactNode {
  if (full.length <= LONG) {
    return (
      <blockquote className="m-0 max-w-[68ch] font-ledger-documentary leading-[1.7]">
        {full}
      </blockquote>
    );
  }

  return (
    <>
      <blockquote className="m-0 max-w-[68ch] font-ledger-documentary leading-[1.7]">
        {`${full.slice(0, LONG).trimEnd()}…`}
      </blockquote>
      <details className="max-w-[68ch]">
        <summary className="min-h-11 cursor-pointer py-2 font-semibold">{label}</summary>
        <blockquote className="m-0 font-ledger-documentary leading-[1.7]">{full}</blockquote>
      </details>
    </>
  );
}

/**
 * An approved source and only the passages this record cites from it. The saved passage and the
 * original page's availability are kept apart: an unreachable page never erases what was relied on.
 * The external link opens in a new tab and sends no referrer.
 */
export function SourceView({
  base,
  copy,
  evidence,
  format,
  source
}: Readonly<{
  base: string;
  copy: Messages["source"];
  evidence: Messages["evidence"];
  format: Formatters;
  source: SourceExcerpts;
}>): ReactNode {
  const { source: item, excerpts } = source;
  const type = Object.hasOwn(copy.types, item.source_type)
    ? copy.types[item.source_type as keyof typeof copy.types]
    : item.source_type;
  const availability = Object.hasOwn(evidence.availability, item.availability)
    ? evidence.availability[item.availability as keyof typeof evidence.availability]
    : item.availability;
  const note = Object.hasOwn(copy.availabilityNote, item.availability)
    ? copy.availabilityNote[item.availability as keyof typeof copy.availabilityNote]
    : undefined;

  return (
    <div className="grid max-w-[76ch] gap-8">
      <header className="grid gap-3">
        <p className="m-0 text-sm font-bold tracking-wide text-muted-foreground uppercase">
          {copy.heading}
        </p>
        <h1 className="m-0 text-[clamp(1.5rem,3vw,2.25rem)] leading-tight [overflow-wrap:anywhere]">
          {item.title}
        </h1>
        <InformationClassMarker labels={evidence.informationClass} value={item.information_class} />
      </header>

      <dl className="m-0 grid gap-3 sm:grid-cols-2 [&_dd]:m-0 [&_dd]:font-semibold [&_dd]:[overflow-wrap:anywhere] [&_dt]:text-sm [&_dt]:text-muted-foreground">
        <div>
          <dt>{copy.facts.publisher}</dt>
          <dd>{item.publisher}</dd>
        </div>
        <div>
          <dt>{copy.facts.type}</dt>
          <dd>{type}</dd>
        </div>
        <div>
          <dt>{copy.facts.availability}</dt>
          <dd>{availability}</dd>
        </div>
        <div>
          <dt>{copy.facts.checked}</dt>
          <dd>
            {item.availability_checked_at === null ? (
              copy.facts.unchecked
            ) : (
              <time dateTime={item.availability_checked_at}>
                {format.date(item.availability_checked_at)}
              </time>
            )}
          </dd>
        </div>
      </dl>
      {note === undefined ? null : <p className="m-0 max-w-[68ch]">{note}</p>}

      <section
        aria-labelledby="passages-heading"
        className="grid gap-4 border-t border-border pt-6"
      >
        <h2 className="m-0 text-ledger-xl" id="passages-heading">
          {copy.excerpts.heading}
        </h2>
        <p className="m-0 text-sm text-muted-foreground">{copy.excerpts.quoteNote}</p>
        {excerpts.length === 0 ? (
          <p className="m-0">{copy.excerpts.empty}</p>
        ) : (
          <ol className="m-0 grid list-none gap-4 p-0">
            {excerpts.map((excerpt) => (
              <li
                className="grid gap-2 border border-border border-s-[0.375rem] border-s-border bg-card p-4"
                key={`${excerpt.cited_by}-${excerpt.item_id}-${excerpt.location_label}`}
              >
                <Passage full={excerpt.passage} label={copy.excerpts.showFull} />
                <p className="m-0 text-sm text-muted-foreground">
                  {copy.excerpts.location}: {excerpt.location_label}
                </p>
                <p className="m-0 flex flex-wrap gap-x-4 text-sm">
                  <span>
                    {excerpt.cited_by === "fact"
                      ? copy.excerpts.supportsFact
                      : copy.excerpts.supportsUpdate}
                  </span>
                  <a href={`${base}#${excerpt.cited_by}-${excerpt.item_id}`}>
                    {copy.excerpts.seeUse}
                  </a>
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="grid max-w-[68ch] gap-2 border-t border-border pt-6">
        <a
          className="inline-flex min-h-11 w-fit items-center font-semibold text-ledger-accent-strong underline"
          href={item.canonical_url}
          referrerPolicy="no-referrer"
          rel="noopener noreferrer"
          target="_blank"
        >
          {copy.original.link}
          <span className="sr-only"> ({copy.original.newTab})</span>
        </a>
        <p className="m-0 text-sm text-muted-foreground">{copy.original.note}</p>
      </section>
    </div>
  );
}
