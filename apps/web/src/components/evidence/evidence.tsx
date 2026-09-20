import type { ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { Glyph } from "@/components/ui/feedback";
import type { components } from "@/lib/api/generated/schema";
import { cn } from "@/lib/utils";

/**
 * Evidence components encode how the product shows truth, not what is true. Every state arrives
 * from the API explicitly; nothing here counts sources, ranks them, or promotes a claim. All text
 * comes in through exhaustive label records, so a locale that lacks a state fails to compile
 * instead of silently falling back. Components are server-renderable and work without JavaScript.
 */

type Schemas = components["schemas"];

export type VerificationState = Schemas["FactOut"]["verification_state"];
export type InformationClass =
  | Schemas["FactOut"]["information_class"]
  | "community_report_unverified"
  | "ai_generated_explanation";
export type TranslationStatus = "reviewed" | "machine_assisted" | "unavailable";
export type SourceAvailability =
  | "unchecked"
  | "available"
  | "temporarily_unavailable"
  | "access_restricted"
  | "permanently_unavailable";

const VERIFICATION_GLYPHS: Readonly<Record<VerificationState, string>> = {
  awaiting_verification: "…",
  verified_official: "✓",
  corroborated: "✓✓",
  community_reviewed: "◇",
  disputed: "≠",
  outdated: "⌛"
};

const VERIFICATION_BORDERS: Readonly<Record<VerificationState, string>> = {
  awaiting_verification: "border-ledger-warning",
  verified_official: "border-ledger-success",
  corroborated: "border-ledger-success",
  community_reviewed: "border-ledger-information",
  disputed: "border-ledger-danger",
  outdated: "border-ledger-warning"
};

const datesClasses =
  "m-0 grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] gap-x-6 gap-y-1 text-sm [&_dt]:text-muted-foreground [&_dd]:m-0 [&_dd]:[overflow-wrap:anywhere]";

const CLASS_GLYPHS: Readonly<Record<InformationClass, string>> = {
  official_source: "O",
  independent_source: "I",
  community_evidence_reviewed: "C",
  community_report_unverified: "?",
  ai_generated_explanation: "AI"
};

/** A localised formatter for an ISO date or timestamp; FE-052 supplies the `Africa/Lagos` one. */
export type DateFormatter = (isoValue: string) => string;

// ---------------------------------------------------------------------------------------------

/** The review state, as words plus a shape. Never derived from how many sources exist. */
export function VerificationLabel({
  labels,
  state
}: Readonly<{
  labels: Readonly<Record<VerificationState, string>>;
  state: VerificationState;
}>): ReactNode {
  return (
    <span
      className={cn(
        "inline-flex items-start gap-2 rounded-lg border bg-card px-2 py-1 text-sm font-bold [overflow-wrap:anywhere]",
        VERIFICATION_BORDERS[state]
      )}
      data-slot="verification-label"
      data-state={state}
    >
      <Glyph className="px-1">{VERIFICATION_GLYPHS[state]}</Glyph>
      {labels[state]}
    </span>
  );
}

export function InformationClassMarker({
  labels,
  value
}: Readonly<{
  labels: Readonly<Record<InformationClass, string>>;
  value: InformationClass;
}>): ReactNode {
  return (
    <span
      className="inline-flex items-start gap-2 text-sm font-semibold text-muted-foreground [overflow-wrap:anywhere]"
      data-slot="class-marker"
      data-class={value}
    >
      <Glyph>{CLASS_GLYPHS[value]}</Glyph>
      {labels[value]}
    </span>
  );
}

export type DateGroupLabels = Readonly<{
  effective: string;
  lastChecked: string;
  published: string;
  retrieved: string;
  /** Shown when a date is absent, so a missing date reads as unknown rather than disappearing. */
  unknown: string;
}>;

/** Only the dates the API supplied are rendered; each is a real `<time>`. */
export function DateGroup({
  dates,
  format,
  labels
}: Readonly<{
  dates: Readonly<{
    effectiveOn?: string | null;
    lastCheckedOn?: string | null;
    publishedOn?: string | null;
    retrievedAt?: string | null;
  }>;
  format: DateFormatter;
  labels: DateGroupLabels;
}>): ReactNode {
  const entries: readonly (readonly [string, string | null | undefined, boolean])[] = [
    [labels.lastChecked, dates.lastCheckedOn, true],
    [labels.effective, dates.effectiveOn, false],
    [labels.published, dates.publishedOn, false],
    [labels.retrieved, dates.retrievedAt, false]
  ];

  return (
    <dl className={datesClasses} data-slot="dates">
      {entries
        // The last-checked date is mandatory on every fact: absence is shown, never hidden.
        .filter(([, value, always]) => always || (value !== undefined && value !== null))
        .map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>
              {value === undefined || value === null ? (
                labels.unknown
              ) : (
                <time dateTime={value}>{format(value)}</time>
              )}
            </dd>
          </div>
        ))}
    </dl>
  );
}

// ---------------------------------------------------------------------------------------------

export type SourceView = Readonly<{
  availability: SourceAvailability;
  availabilityCheckedAt: string | null;
  canonicalUrl: string;
  id: string;
  informationClass: InformationClass;
  publisher: string;
  title: string;
}>;

export type SourceCardLabels = Readonly<{
  availability: Readonly<Record<SourceAvailability, string>>;
  availabilityHeading: string;
  classes: Readonly<Record<InformationClass, string>>;
  externalNotice: string;
  publisherHeading: string;
  unknownDate: string;
}>;

/** Source identity and whether it can currently be reached. Approved sources only. */
export function SourceCard({
  format,
  labels,
  source
}: Readonly<{ format: DateFormatter; labels: SourceCardLabels; source: SourceView }>): ReactNode {
  return (
    <article
      className="grid gap-2 border border-border bg-card p-3"
      data-slot="source-card"
      id={`source-${source.id}`}
    >
      <h3 className="m-0 text-base [overflow-wrap:anywhere]">
        <a href={source.canonicalUrl} rel="noopener noreferrer" target="_blank">
          {source.title} <span className="sr-only">({labels.externalNotice})</span>
        </a>
      </h3>
      <InformationClassMarker labels={labels.classes} value={source.informationClass} />
      <dl className={datesClasses} data-slot="dates">
        <div>
          <dt>{labels.publisherHeading}</dt>
          <dd>{source.publisher}</dd>
        </div>
        <div>
          <dt>{labels.availabilityHeading}</dt>
          <dd>
            {labels.availability[source.availability]}
            {source.availabilityCheckedAt === null ? null : (
              <>
                {" "}
                <time dateTime={source.availabilityCheckedAt}>
                  {format(source.availabilityCheckedAt)}
                </time>
              </>
            )}
          </dd>
        </div>
      </dl>
    </article>
  );
}

// ---------------------------------------------------------------------------------------------

export type CitationView = Readonly<{
  /** Stable identifier shared by the claim's trigger and the source entry. */
  id: string;
  label: string;
  locationLabel: string;
  passage: string;
  publisher: string;
  sourceTitle: string;
}>;

/**
 * A claim with its cited-source controls. The controls are ordinary in-page links, so the
 * "citation stitch" works with no JavaScript: activating one moves focus to the source entry, and
 * `:target` styling gives both ends the same persistent identifier. A claim with no citation is
 * refused (renders nothing) because an uncited public statement must never appear.
 */
export function ClaimWithCitations({
  citations,
  citedLabel,
  claimId,
  children,
  verification
}: Readonly<{
  children: ReactNode;
  citations: readonly CitationView[];
  citedLabel: string;
  claimId: string;
  verification?: ReactNode;
}>): ReactNode {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div
      className="grid gap-2 border-t border-border py-3"
      data-slot="claim"
      id={`claim-${claimId}`}
    >
      <p className="m-0 max-w-[68ch] [overflow-wrap:anywhere]">{children}</p>
      {verification}
      <ul aria-label={citedLabel} className="m-0 flex list-none flex-wrap gap-2 p-0">
        {citations.map((citation) => (
          <li key={citation.id}>
            <a
              aria-describedby={`citation-${citation.id}`}
              className={cn(buttonVariants({ variant: "secondary" }), "text-sm")}
              data-slot="citation-trigger"
              href={`#citation-${citation.id}`}
            >
              {citation.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The other end of the stitch: a quoted passage in the documentary face, with its location. */
export function CitationEntry({
  backHref,
  backLabel,
  citation
}: Readonly<{ backHref: string; backLabel: string; citation: CitationView }>): ReactNode {
  return (
    <li
      className="grid list-none gap-1 border border-border border-s-[0.375rem] border-s-border bg-card p-3 [overflow-wrap:anywhere] target:border-s-primary target:outline-[length:var(--focus-width)] target:outline-offset-[var(--focus-offset)] target:outline-ring target:outline-solid"
      data-slot="citation-entry"
      id={`citation-${citation.id}`}
      tabIndex={-1}
    >
      <span className="font-extrabold">{citation.label}</span>
      <blockquote className="m-0 max-w-[68ch] font-ledger-documentary leading-[1.7]">
        {citation.passage}
      </blockquote>
      <p className="m-0 text-sm text-muted-foreground">
        {citation.sourceTitle}, {citation.publisher}, {citation.locationLabel}
      </p>
      <a href={backHref}>{backLabel}</a>
    </li>
  );
}

// ---------------------------------------------------------------------------------------------

export type TimelineOrigin = "official" | "community_reviewed";

/** Official and reviewed-community entries differ by words and shape, not only colour. */
export function TimelineItem({
  children,
  date,
  dateLabel,
  format,
  origin,
  originLabels,
  verification
}: Readonly<{
  children: ReactNode;
  date: string | null;
  dateLabel: string;
  format: DateFormatter;
  origin: TimelineOrigin;
  originLabels: Readonly<Record<TimelineOrigin, string>>;
  verification: ReactNode;
}>): ReactNode {
  return (
    <li
      className={cn(
        "grid list-none gap-2 border-s-[0.375rem] px-4 py-2",
        origin === "official"
          ? "border-s-primary border-solid"
          : "border-s-ledger-information border-dashed"
      )}
      data-origin={origin}
      data-slot="timeline-item"
    >
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Glyph>{origin === "official" ? "O" : "C"}</Glyph>
        <strong>{originLabels[origin]}</strong>
        {date === null ? null : (
          <span>
            {dateLabel} <time dateTime={date}>{format(date)}</time>
          </span>
        )}
      </div>
      <div>{children}</div>
      {verification}
    </li>
  );
}

// ---------------------------------------------------------------------------------------------

export function TranslationNotice({
  labels,
  status
}: Readonly<{
  labels: Readonly<Record<TranslationStatus, string>>;
  status: TranslationStatus;
}>): ReactNode {
  // A reviewed translation needs no warning; every other state is stated plainly.
  return status === "reviewed" ? null : (
    <p
      className="m-0 flex items-start gap-2 rounded-ledger-control border border-border bg-card p-3 [overflow-wrap:anywhere]"
      data-slot="translation-notice"
      data-status={status}
      role="note"
    >
      <Glyph>T</Glyph>
      {labels[status]}
    </p>
  );
}

/** AI text is an explanation, never a source, and always says so in words. */
export function AiExplanationNotice({
  children,
  label
}: Readonly<{ children: ReactNode; label: string }>): ReactNode {
  return (
    <div
      className="grid gap-2 rounded-ledger-control border border-dashed border-border bg-card p-3 [overflow-wrap:anywhere]"
      data-slot="ai-notice"
      role="note"
    >
      <strong className="flex items-start gap-2">
        <Glyph>AI</Glyph>
        {label}
      </strong>
      <div>{children}</div>
    </div>
  );
}

export type EvidenceGapKind = "contradiction" | "information_gap" | "insufficient_evidence";

const GAP_BORDERS: Readonly<Record<EvidenceGapKind, string>> = {
  contradiction: "border-s-ledger-danger",
  information_gap: "border-s-ledger-warning",
  insufficient_evidence: "border-s-double border-s-ledger-muted"
};

const GAP_GLYPHS: Readonly<Record<EvidenceGapKind, string>> = {
  contradiction: "≠",
  information_gap: "?",
  insufficient_evidence: "∅"
};

/** Contradictions, unknowns, and refusals are distinct states, each with its own shape and title. */
export function EvidenceGap({
  children,
  kind,
  title
}: Readonly<{ children?: ReactNode; kind: EvidenceGapKind; title: string }>): ReactNode {
  return (
    <div
      className={cn(
        "grid gap-2 rounded-ledger-control border border-border border-s-[0.375rem] bg-card p-3 [overflow-wrap:anywhere]",
        GAP_BORDERS[kind]
      )}
      data-gap={kind}
      data-slot="evidence-gap"
      role="note"
    >
      <strong className="flex items-start gap-2">
        <Glyph>{GAP_GLYPHS[kind]}</Glyph>
        {title}
      </strong>
      {children === undefined ? null : <div>{children}</div>}
    </div>
  );
}
