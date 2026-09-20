import type { ReactNode } from "react";

import type { components } from "@/lib/api/generated/schema";

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

const CLASS_GLYPHS: Readonly<Record<InformationClass, string>> = {
  official_source: "O",
  independent_source: "I",
  community_evidence_reviewed: "C",
  community_report_unverified: "?",
  ai_generated_explanation: "AI"
};

/** A localised formatter for an ISO date or timestamp; FE-052 supplies the `Africa/Lagos` one. */
export type DateFormatter = (isoValue: string) => string;

function Glyph({ children }: Readonly<{ children: ReactNode }>): ReactNode {
  return (
    <span aria-hidden="true" className="primitive-glyph evidence-glyph">
      {children}
    </span>
  );
}

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
    <span className={`primitive-status evidence-verification evidence-verification--${state}`}>
      <Glyph>{VERIFICATION_GLYPHS[state]}</Glyph>
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
    <span className={`evidence-class evidence-class--${value}`}>
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
    <dl className="evidence-dates">
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
    <article className="evidence-source" id={`source-${source.id}`}>
      <h3 className="evidence-source-title">
        <a href={source.canonicalUrl} rel="noopener noreferrer" target="_blank">
          {source.title} <span className="sr-only">({labels.externalNotice})</span>
        </a>
      </h3>
      <InformationClassMarker labels={labels.classes} value={source.informationClass} />
      <dl className="evidence-dates">
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
    <div className="evidence-claim" id={`claim-${claimId}`}>
      <p className="evidence-claim-text">{children}</p>
      {verification}
      <ul aria-label={citedLabel} className="evidence-citations">
        {citations.map((citation) => (
          <li key={citation.id}>
            <a
              aria-describedby={`citation-${citation.id}`}
              className="primitive-button primitive-button--secondary evidence-cite"
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
    <li className="evidence-citation-entry" id={`citation-${citation.id}`} tabIndex={-1}>
      <span className="evidence-citation-id">{citation.label}</span>
      <blockquote className="evidence-passage">{citation.passage}</blockquote>
      <p className="evidence-citation-meta">
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
    <li className={`evidence-timeline-item evidence-timeline-item--${origin}`}>
      <div className="evidence-timeline-meta">
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
    <p className={`evidence-notice evidence-notice--${status}`} role="note">
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
    <div className="evidence-ai" role="note">
      <strong>
        <Glyph>AI</Glyph>
        {label}
      </strong>
      <div>{children}</div>
    </div>
  );
}

export type EvidenceGapKind = "contradiction" | "information_gap" | "insufficient_evidence";

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
    <div className={`evidence-gap evidence-gap--${kind}`} role="note">
      <strong>
        <Glyph>{GAP_GLYPHS[kind]}</Glyph>
        {title}
      </strong>
      {children === undefined ? null : <div>{children}</div>}
    </div>
  );
}
