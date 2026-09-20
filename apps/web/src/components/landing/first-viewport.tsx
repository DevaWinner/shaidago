import type { ReactNode } from "react";

import {
  CitationEntry,
  ClaimWithCitations,
  DateGroup,
  TimelineItem,
  VerificationLabel,
  type DateFormatter
} from "@/components/evidence/evidence";
import { ButtonLink } from "@/components/ui/button";
import type { Messages } from "@/i18n/catalogue";

/**
 * The first viewport from the Field ledger contract: a locality-tagged record in a reading field,
 * a dated evidence rail beside it on wide screens (after it on small ones), browse as the primary
 * action and private reporting clearly secondary. Everything is server-rendered HTML; the
 * citation control is an ordinary in-page link.
 */
export function FirstViewport({
  browseHref,
  evidence,
  format,
  messages,
  reportHref,
  sourceCountText,
  sourceLabelText
}: Readonly<{
  browseHref: string;
  evidence: Messages["evidence"];
  format: DateFormatter;
  messages: Messages["landing"];
  reportHref: string;
  /** ICU-formatted in the page's language, e.g. "1 source". */
  sourceCountText: string;
  sourceLabelText: string;
}>): ReactNode {
  const sample = messages.sample;
  const citation = {
    id: "example-1",
    label: sourceLabelText,
    ...sample.citation
  };

  return (
    <section
      aria-labelledby="landing-title"
      className="grid gap-8 lg:grid-cols-12 lg:items-start lg:gap-x-6"
      data-slot="first-viewport"
    >
      <div
        className="grid min-w-0 content-start gap-4 lg:col-span-7 lg:col-start-1"
        data-slot="fv-record"
      >
        <p className="m-0 flex flex-wrap gap-2 text-sm font-bold tracking-wide text-muted-foreground uppercase">
          <span>{messages.localityLabel}</span>
          <span aria-hidden="true">·</span>
          <span>{messages.recordKind}</span>
        </p>
        <h1
          className="m-0 max-w-[24ch] text-[clamp(1.75rem,3.4vw,2.75rem)] leading-[1.1] [overflow-wrap:anywhere]"
          data-slot="fv-title"
          id="landing-title"
        >
          {messages.heading}
        </h1>
        <p className="m-0 max-w-[60ch]">{messages.lead}</p>

        <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-start">
          <ButtonLink className="px-6 text-ledger-lg" data-slot="fv-primary" href={browseHref}>
            {messages.browse}
          </ButtonLink>
          <div
            className="grid justify-items-stretch gap-2 sm:justify-items-start"
            data-slot="fv-secondary"
          >
            <ButtonLink href={reportHref} variant="secondary">
              {messages.report}
            </ButtonLink>
            <p className="m-0 max-w-[40ch] text-sm text-muted-foreground">{messages.reportNote}</p>
          </div>
        </div>

        <article
          aria-labelledby="sample-title"
          className="grid gap-3 border border-border border-s-[0.375rem] border-s-primary bg-card px-4 py-4 sm:px-6"
          data-slot="fv-entry"
        >
          <p className="m-0 text-sm text-muted-foreground" role="note">
            <strong>{sample.noticeTitle}.</strong> {sample.notice}
          </p>
          <h2
            className="m-0 text-ledger-xl leading-[1.1] [overflow-wrap:anywhere]"
            id="sample-title"
          >
            {sample.heading}
          </h2>
          <p className="m-0 max-w-[68ch]">{sample.promised}</p>
          <ClaimWithCitations
            citations={[citation]}
            citedLabel={messages.citedLabel}
            claimId="example"
            verification={
              <VerificationLabel labels={evidence.verification} state="awaiting_verification" />
            }
          >
            <strong>{sample.stateLabel}:</strong> {sample.stateText}
          </ClaimWithCitations>
          <dl className="m-0 flex flex-wrap gap-x-6 gap-y-2 text-sm [&_dd]:m-0 [&_dd]:font-bold [&_dt]:text-muted-foreground">
            <div>
              <dt>{sourceLabelText}</dt>
              <dd>{sourceCountText}</dd>
            </div>
          </dl>
          <DateGroup
            dates={{ lastCheckedOn: "2026-09-01" }}
            format={format}
            labels={evidence.dates}
          />
        </article>
      </div>

      <aside
        aria-labelledby="rail-title"
        className="grid min-w-0 content-start gap-4 border-t border-border pt-4 lg:col-span-4 lg:col-start-9 lg:border-s lg:border-t-0 lg:ps-6 lg:pt-0"
        data-slot="fv-rail"
      >
        <h2 className="m-0 text-ledger-lg" id="rail-title">
          {messages.evidenceHeading}
        </h2>
        <ol className="m-0 grid gap-3 p-0">
          <TimelineItem
            date="2026-09-01"
            dateLabel={evidence.dates.lastChecked}
            format={format}
            origin="official"
            originLabels={evidence.timeline}
            verification={
              <VerificationLabel labels={evidence.verification} state="awaiting_verification" />
            }
          >
            {sample.railEntries.official}
          </TimelineItem>
          <TimelineItem
            date="2026-08-20"
            dateLabel={evidence.dates.effective}
            format={format}
            origin="community_reviewed"
            originLabels={evidence.timeline}
            verification={
              <VerificationLabel labels={evidence.verification} state="community_reviewed" />
            }
          >
            {sample.railEntries.community}
          </TimelineItem>
        </ol>
        <ol className="m-0 grid gap-3 p-0">
          <CitationEntry
            backHref="#claim-example"
            backLabel={messages.citationBack}
            citation={citation}
          />
        </ol>
      </aside>
    </section>
  );
}
