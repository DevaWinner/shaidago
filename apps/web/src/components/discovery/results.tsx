import type { ReactNode } from "react";

import { Callout, StatusLabel } from "@/components/ui/feedback";
import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import type { Formatters } from "@/lib/format/formatters";
import {
  groupDuplicates,
  type AnalysisView,
  type RunView,
  type SourceView
} from "@/lib/discovery/parse";

export type DiscoveryCopy = Messages["discovery"];

const lookup = (table: object, key: string, fallback: string): string =>
  (table as Readonly<Record<string, string | undefined>>)[key] ?? fallback;

/** Every result carries the same unreviewed label, written by our copy and never taken from the server. */
export function UnreviewedLabel({ copy }: Readonly<{ copy: DiscoveryCopy }>): ReactNode {
  return <StatusLabel tone="limited-evidence">{copy.label}</StatusLabel>;
}

function SourceCard({
  copy,
  extra,
  format,
  source,
  index
}: Readonly<{
  copy: DiscoveryCopy;
  extra?: ReactNode;
  format: Formatters;
  index: number;
  source: SourceView;
}>): ReactNode {
  const words = copy.card;

  return (
    <li
      className="grid gap-2 border border-border bg-card p-3"
      data-disposition={source.disposition}
      data-slot="discovery-source"
      id={`source-${source.id}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <UnreviewedLabel copy={copy} />
        <span className="text-sm font-semibold">
          {formatMessageLite(copy.analysis.sourceRef, { number: index + 1 })}
        </span>
      </div>
      <strong className="text-ledger-lg [overflow-wrap:anywhere]">
        {source.title ?? words.untitled}
      </strong>
      <p className="m-0 text-sm [overflow-wrap:anywhere]">
        {words.publisher}: {source.publisher} · {words.type}: {source.type}
      </p>
      <p className="m-0 text-sm">
        {source.publishedOn === null
          ? words.publishedUnknown
          : formatMessageLite(words.published, {
              date: format.date(source.publishedOn),
              provenance: source.provenance
            })}
        {source.dateConflict ? ` ${words.dateConflict}` : ""}
      </p>
      <p className="m-0 text-sm">
        {words.availability}:{" "}
        {lookup(copy.availabilityStates, source.availability, source.availability)}
        {source.discoveredAt === undefined
          ? ""
          : ` · ${formatMessageLite(words.discovered, { date: format.dateTime(source.discoveredAt) })}`}
        {source.retrievedAt === undefined
          ? ""
          : ` · ${formatMessageLite(words.retrieved, { date: format.dateTime(source.retrievedAt) })}`}
      </p>
      {source.injectionFlag ? (
        <Callout title={words.injection} tone="warning">
          {null}
        </Callout>
      ) : null}
      <blockquote className="m-0 border-s-[0.375rem] border-border ps-3 font-ledger-documentary [overflow-wrap:anywhere]">
        <span className="sr-only">{words.excerpt}: </span>
        {source.excerpt}
      </blockquote>
      <p className="m-0">
        {source.url === undefined ? (
          <small>{words.noLink}</small>
        ) : (
          <a
            className="font-semibold underline"
            href={source.url}
            rel="noopener noreferrer nofollow"
            target="_blank"
          >
            {words.open}
          </a>
        )}
      </p>
      {extra}
    </li>
  );
}

/** Ten cards at most, with repeated pages grouped under the page they repeat. */
export function SourceList({
  copy,
  format,
  renderExtra,
  sources
}: Readonly<{
  copy: DiscoveryCopy;
  format: Formatters;
  renderExtra?: ((source: SourceView) => ReactNode) | undefined;
  sources: readonly SourceView[];
}>): ReactNode {
  if (sources.length === 0) {
    return <p className="m-0">{copy.results.none}</p>;
  }

  const index = new Map(sources.map((source, position) => [source.id, position]));

  return (
    <ol className="m-0 grid list-none gap-3 p-0" data-slot="discovery-sources">
      {groupDuplicates(sources).map(({ primary, duplicates }) => (
        <li className="grid gap-2" key={primary.id}>
          <ol className="m-0 grid list-none gap-2 p-0">
            <SourceCard
              copy={copy}
              extra={renderExtra?.(primary)}
              format={format}
              index={index.get(primary.id) ?? 0}
              source={primary}
            />
          </ol>
          {duplicates.length === 0 ? null : (
            <div className="grid gap-2 ps-4" data-slot="discovery-duplicates">
              <strong className="text-sm">{copy.card.repeatsHeading}</strong>
              <ol className="m-0 grid list-none gap-2 p-0">
                {duplicates.map((duplicate) => (
                  <SourceCard
                    copy={copy}
                    extra={renderExtra?.(duplicate)}
                    format={format}
                    index={index.get(duplicate.id) ?? 0}
                    key={duplicate.id}
                    source={duplicate}
                  />
                ))}
              </ol>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

function Refs({
  all,
  copy,
  sources
}: Readonly<{
  all: readonly SourceView[];
  copy: DiscoveryCopy;
  sources: readonly number[];
}>): ReactNode {
  return (
    <span className="whitespace-nowrap text-sm">
      {sources.map((position, order) => (
        <a
          aria-label={formatMessageLite(copy.analysis.sourceRef, { number: position + 1 })}
          className="me-1 underline"
          href={`#source-${all[position]?.id ?? ""}`}
          key={`${position}-${order}`}
        >
          [{position + 1}]
        </a>
      ))}
    </span>
  );
}

/**
 * The analysis sections stay separate: supported facts (each with its sentence citations),
 * claims attributed to their source, both sides of any contradiction, gaps, and the safety note.
 * There is no score, rank, or confidence: those are not evidence.
 */
export function AnalysisSections({
  analysis,
  copy,
  sources
}: Readonly<{
  analysis: AnalysisView | undefined;
  copy: DiscoveryCopy;
  sources: readonly SourceView[];
}>): ReactNode {
  const words = copy.analysis;

  if (analysis === undefined) {
    return (
      <Callout title={words.heading} tone="information">
        {words.unavailable}
      </Callout>
    );
  }

  const none = <p className="m-0 text-sm">{words.none}</p>;

  return (
    <section
      aria-label={words.heading}
      className="grid gap-3 border-2 border-double border-border p-3"
      data-slot="discovery-analysis"
    >
      <h3 className="m-0 text-base">{words.heading}</h3>
      <div>
        <h4 className="m-0 text-sm">{words.facts}</h4>
        {analysis.facts.length === 0 ? (
          none
        ) : (
          <ul className="m-0 grid gap-1 ps-5" data-section="facts">
            {analysis.facts.map((fact) => (
              <li key={fact.text}>
                {fact.text} <Refs all={sources} copy={copy} sources={fact.sources} />
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4 className="m-0 text-sm">{words.claims}</h4>
        {analysis.claims.length === 0 ? (
          none
        ) : (
          <ul className="m-0 grid gap-1 ps-5" data-section="claims">
            {analysis.claims.map((claim) => (
              <li key={`${claim.publisher}-${claim.claim}`}>
                {formatMessageLite(words.claimBy, {
                  publisher: claim.publisher,
                  claim: claim.claim
                })}{" "}
                <Refs all={sources} copy={copy} sources={[claim.source]} />
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4 className="m-0 text-sm">{words.contradictions}</h4>
        {analysis.contradictions.length === 0 ? (
          none
        ) : (
          <ul className="m-0 grid gap-1 ps-5" data-section="contradictions">
            {analysis.contradictions.map((item) => (
              <li key={item.description}>
                {item.description} <small>{words.sides}:</small>{" "}
                <Refs all={sources} copy={copy} sources={item.sources} />
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4 className="m-0 text-sm">{words.gaps}</h4>
        {analysis.gaps.length === 0 ? (
          none
        ) : (
          <ul className="m-0 grid gap-1 ps-5" data-section="gaps">
            {analysis.gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        )}
      </div>
      <p className="m-0" data-section="safety">
        <strong>{words.safety}:</strong> {analysis.safety}
      </p>
      <small className="text-muted-foreground">{words.noScore}</small>
    </section>
  );
}

/** The run's stage, real counts, replay or live, and dates. No percentage is ever invented. */
export function RunSummary({
  copy,
  format,
  run
}: Readonly<{ copy: DiscoveryCopy; format: Formatters; run: RunView }>): ReactNode {
  const words = copy.status;

  return (
    <div className="grid gap-1" data-slot="discovery-summary">
      <StatusLabel
        tone={
          run.status === "complete"
            ? "reviewed"
            : run.status === "failed" || run.status === "cancelled"
              ? "problem"
              : "under-review"
        }
      >
        {words.label}: {lookup(words.states, run.status, run.status)}
      </StatusLabel>
      <p className="m-0 text-sm">
        {formatMessageLite(words.counts, {
          found: run.counts.found,
          fetched: run.counts.fetched,
          analysed: run.counts.analysed
        })}
      </p>
      <p className="m-0 text-sm text-muted-foreground">
        {lookup(words.scope, run.scope, "")} · {run.demoReplay ? words.replay : words.live}
      </p>
      <p className="m-0 text-sm text-muted-foreground">
        {formatMessageLite(words.started, { date: format.dateTime(run.createdAt) })}
        {run.finishedAt === null
          ? ""
          : ` · ${formatMessageLite(words.finished, { date: format.dateTime(run.finishedAt) })}`}
      </p>
    </div>
  );
}

/** Failure and cancellation say what happened and what is (or is not) still shown. */
export function RunOutcome({
  copy,
  run
}: Readonly<{ copy: DiscoveryCopy; run: RunView }>): ReactNode {
  const partial = run.sources.length > 0;

  if (run.status === "failed") {
    return (
      <Callout title={copy.failure.title} tone="danger">
        <p className="m-0">
          {run.failureCode === null
            ? copy.failure.generic
            : lookup(copy.failure.codes, run.failureCode, copy.failure.generic)}
        </p>
        <p className="m-0">{partial ? copy.failure.partial : copy.failure.empty}</p>
      </Callout>
    );
  }
  if (run.status === "cancelled") {
    return (
      <Callout title={copy.status.states.cancelled} tone="warning">
        {partial ? copy.states.cancelledPartial : copy.states.cancelledEmpty}
      </Callout>
    );
  }

  return null;
}
