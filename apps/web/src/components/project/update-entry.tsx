import type { ReactNode } from "react";

import {
  ClaimWithCitations,
  InformationClassMarker,
  TimelineItem,
  VerificationLabel,
  type CitationView
} from "@/components/evidence/evidence";
import type { Messages } from "@/i18n/catalogue";
import { formatMessage } from "@/i18n/format-message";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { Citation, Fact, ProjectUpdate } from "@/lib/api/public-data";
import { isFutureDate } from "@/lib/directory/freshness";
import { formatMessageLite } from "@/lib/directory/format-lite";
import type { Formatters } from "@/lib/format/formatters";

export type EntryCopy = Readonly<{
  directory: Messages["directory"];
  evidence: Messages["evidence"];
  project: Messages["project"];
  source: Messages["source"];
}>;

export type Statement = Fact | ProjectUpdate;

export function citationView(
  claimId: string,
  citation: Citation,
  index: number,
  copy: EntryCopy,
  language: ApiLocale
): CitationView {
  return {
    id: `${claimId}-${index + 1}`,
    label: formatMessage(language, copy.project.facts.sourceLabel, { number: index + 1 }),
    locationLabel: citation.location_label,
    passage: citation.passage,
    publisher: citation.publisher,
    sourceTitle: citation.source_title
  };
}

/** One public statement with its verification, information class, and cited-source controls. */
export function StatementClaim({
  claimId,
  copy,
  language,
  statement
}: Readonly<{
  claimId: string;
  copy: EntryCopy;
  language: ApiLocale;
  statement: Statement;
}>): ReactNode {
  const text = copy.project;
  const views = statement.citations.map((citation, index) =>
    citationView(claimId, citation, index, copy, language)
  );

  return (
    <ClaimWithCitations
      citations={views}
      citedLabel={text.facts.citedLabel}
      claimId={claimId}
      triggerName={(view) =>
        formatMessageLite(text.facts.triggerName, {
          label: view.label,
          statement: statement.statement
        })
      }
      verification={
        <div className="flex flex-wrap items-start gap-3">
          <VerificationLabel
            labels={copy.evidence.verification}
            state={statement.verification_state}
          />
          <InformationClassMarker
            labels={copy.evidence.informationClass}
            value={statement.information_class}
          />
          <span className="text-sm text-muted-foreground">
            {formatMessage(language, text.facts.sourceCount, { count: statement.citations.length })}
          </span>
        </div>
      }
    >
      {statement.statement}
    </ClaimWithCitations>
  );
}

/**
 * One entry of a project's public timeline. The public record page and the reviewer's exact
 * preview both render this component from the same update shape, so what a reviewer confirms is
 * what the public later sees. It must be placed inside an ordered list.
 */
export function PublicUpdateEntry({
  claimId,
  copy,
  format,
  language,
  now,
  update
}: Readonly<{
  claimId: string;
  copy: EntryCopy;
  format: Formatters;
  language: ApiLocale;
  now: Date;
  update: ProjectUpdate;
}>): ReactNode {
  const text = copy.project;

  return (
    <TimelineItem
      date={update.effective_on}
      dateLabel={
        isFutureDate(update.effective_on, now) ? text.timeline.scheduled : text.timeline.date
      }
      format={format.date}
      origin={
        update.information_class === "community_evidence_reviewed"
          ? "community_reviewed"
          : "official"
      }
      originLabels={copy.evidence.timeline}
      verification={null}
    >
      <StatementClaim claimId={claimId} copy={copy} language={language} statement={update} />
    </TimelineItem>
  );
}
