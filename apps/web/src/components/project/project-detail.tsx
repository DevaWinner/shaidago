import type { ReactNode } from "react";

import {
  CitationEntry,
  ClaimWithCitations,
  DateGroup,
  EvidenceGap,
  InformationClassMarker,
  TimelineItem,
  VerificationLabel,
  type CitationView
} from "@/components/evidence/evidence";
import { ButtonLink } from "@/components/ui/button";
import { formatMessage, type Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { Citation, Fact, ProjectDetail, ProjectUpdate } from "@/lib/api/public-data";
import { STALE_AFTER_DAYS, isFutureDate, isStale } from "@/lib/directory/freshness";
import { formatMessageLite } from "@/lib/directory/format-lite";
import type { Formatters } from "@/lib/format/formatters";

type Copy = Readonly<{
  directory: Messages["directory"];
  evidence: Messages["evidence"];
  project: Messages["project"];
  source: Messages["source"];
}>;

const section = "grid gap-4 border-t border-border pt-8";
const heading = "m-0 text-ledger-xl leading-tight";

type Statement = Fact | ProjectUpdate;

function citationView(
  claimId: string,
  citation: Citation,
  index: number,
  copy: Copy,
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

/**
 * The record, in the order a resident needs it: what was promised, the current recorded state, what
 * the sources say (each statement with its own verification and citations), updates over time, what
 * is not known, and safe next steps. Facts are never merged into one summary, and nothing implies
 * all sources are verified equally: every statement carries its own label.
 */
export function ProjectDetailView({
  copy,
  format,
  language,
  localityName,
  locale,
  now,
  project
}: Readonly<{
  copy: Copy;
  format: Formatters;
  language: ApiLocale;
  localityName: string;
  locale: string;
  now: Date;
  project: ProjectDetail;
}>): ReactNode {
  const text = copy.project;
  const base = `/${locale}/projects/${encodeURIComponent(project.slug)}`;
  const stale = isStale(project.last_checked_on, now);
  const facts = project.facts.filter((fact) => fact.citations.length > 0);
  const updates = project.updates.filter((update) => update.citations.length > 0);
  const uncertain = facts.filter((fact) =>
    ["awaiting_verification", "disputed", "outdated"].includes(fact.verification_state)
  );

  const evidence = [
    ...facts.map((fact) => ({ id: `fact-${fact.id}`, statement: fact })),
    ...updates.map((update) => ({ id: `update-${update.id}`, statement: update }))
  ].flatMap(({ id, statement }) =>
    statement.citations.map((citation, index) => ({
      claimId: id,
      citation,
      view: citationView(id, citation, index, copy, language)
    }))
  );

  const claim = (statement: Statement, claimId: string): ReactNode => {
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
              {formatMessage(language, text.facts.sourceCount, {
                count: statement.citations.length
              })}
            </span>
          </div>
        }
      >
        {statement.statement}
      </ClaimWithCitations>
    );
  };

  return (
    <div className="grid gap-10 lg:grid-cols-12 lg:gap-x-8">
      <div className="grid min-w-0 content-start gap-10 lg:col-span-8">
        <header className="grid gap-3">
          <p className="m-0 flex flex-wrap gap-2 text-sm font-bold tracking-wide text-muted-foreground uppercase">
            <span>{localityName}</span>
            <span aria-hidden="true">·</span>
            <span>{copy.directory.categories[project.category]}</span>
          </p>
          <h1
            className="m-0 max-w-[24ch] text-[clamp(1.75rem,3.4vw,2.75rem)] leading-[1.1] [overflow-wrap:anywhere]"
            lang={project.text.served_locale}
          >
            {project.text.title}
          </h1>
          <p className="m-0 max-w-[68ch] text-ledger-lg" lang={project.text.served_locale}>
            {project.text.summary}
          </p>
        </header>

        <section aria-labelledby="promised-heading" className={section}>
          <h2 className={heading} id="promised-heading">
            {text.promised.heading}
          </h2>
          {project.text.promised_deliverable.trim() === "" ? (
            <EvidenceGap kind="information_gap" title={text.promised.notRecorded} />
          ) : (
            <p className="m-0 max-w-[68ch]" lang={project.text.served_locale}>
              {project.text.promised_deliverable}
            </p>
          )}
        </section>

        <section aria-labelledby="state-heading" className={section}>
          <h2 className={heading} id="state-heading">
            {text.state.heading}
          </h2>
          <dl className="m-0 flex flex-wrap gap-x-8 gap-y-2 [&_dd]:m-0 [&_dd]:font-semibold [&_dt]:text-sm [&_dt]:text-muted-foreground">
            <div>
              <dt>{text.state.status}</dt>
              <dd>{copy.directory.statuses[project.public_status]}</dd>
            </div>
            <div>
              <dt>{text.state.lastChecked}</dt>
              <dd>
                {project.last_checked_on === null ? (
                  text.state.notChecked
                ) : (
                  <time dateTime={project.last_checked_on}>
                    {format.date(project.last_checked_on)}
                  </time>
                )}
              </dd>
            </div>
          </dl>
          <p className="m-0 max-w-[68ch] text-sm text-muted-foreground">{text.state.caveat}</p>
          {stale ? (
            <EvidenceGap
              kind="information_gap"
              title={formatMessage(language, text.state.stale, { days: STALE_AFTER_DAYS })}
            />
          ) : null}
        </section>

        <section aria-labelledby="facts-heading" className={section}>
          <h2 className={heading} id="facts-heading">
            {text.facts.heading}
          </h2>
          {facts.length === 0 ? (
            <p className="m-0 max-w-[68ch]">{text.facts.empty}</p>
          ) : (
            <ul className="m-0 grid list-none gap-2 p-0">
              {facts.map((fact) => (
                <li className="grid gap-2" id={`fact-${fact.id}`} key={fact.id}>
                  {claim(fact, `fact-${fact.id}`)}
                  <DateGroup
                    dates={{ effectiveOn: fact.effective_on, lastCheckedOn: fact.last_checked_on }}
                    format={format.date}
                    labels={copy.evidence.dates}
                  />
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="timeline-heading" className={section}>
          <h2 className={heading} id="timeline-heading">
            {text.timeline.heading}
          </h2>
          {updates.length === 0 ? (
            <p className="m-0 max-w-[68ch]">{text.timeline.empty}</p>
          ) : (
            <ol className="m-0 grid gap-4 p-0">
              {updates.map((update) => (
                <TimelineItem
                  date={update.effective_on}
                  dateLabel={
                    isFutureDate(update.effective_on, now)
                      ? text.timeline.scheduled
                      : text.timeline.date
                  }
                  format={format.date}
                  key={update.id}
                  origin={
                    update.information_class === "community_evidence_reviewed"
                      ? "community_reviewed"
                      : "official"
                  }
                  originLabels={copy.evidence.timeline}
                  verification={null}
                >
                  {claim(update, `update-${update.id}`)}
                </TimelineItem>
              ))}
            </ol>
          )}
        </section>

        <section aria-labelledby="unknown-heading" className={section}>
          <h2 className={heading} id="unknown-heading">
            {text.unknown.heading}
          </h2>
          {uncertain.length === 0 ? (
            <p className="m-0 max-w-[68ch]">{text.unknown.none}</p>
          ) : (
            <ul className="m-0 grid list-none gap-3 p-0">
              {uncertain.map((fact) => {
                const state = fact.verification_state;
                const template =
                  state === "disputed"
                    ? text.unknown.disputed
                    : state === "outdated"
                      ? text.unknown.outdated
                      : text.unknown.awaiting;

                return (
                  <li key={fact.id}>
                    <EvidenceGap
                      kind={state === "disputed" ? "contradiction" : "information_gap"}
                      title={formatMessageLite(template, { statement: fact.statement })}
                    >
                      <a href={`#fact-${fact.id}`}>{text.facts.back}</a>
                    </EvidenceGap>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section aria-labelledby="actions-heading" className={section}>
          <h2 className={heading} id="actions-heading">
            {text.actions.heading}
          </h2>
          <div className="grid max-w-[40ch] gap-2">
            <ButtonLink
              href={`/${locale}/report?project=${encodeURIComponent(project.slug)}`}
              variant="secondary"
            >
              {text.actions.report}
            </ButtonLink>
            <p className="m-0 text-sm text-muted-foreground">{text.actions.note}</p>
          </div>
        </section>
      </div>

      <aside
        aria-labelledby="evidence-heading"
        className="grid min-w-0 content-start gap-4 lg:col-span-4 lg:border-s lg:border-border lg:ps-6"
        data-slot="evidence-rail"
      >
        <h2 className="m-0 text-ledger-lg" id="evidence-heading">
          {text.facts.evidenceHeading}
        </h2>
        <ol className="m-0 grid gap-3 p-0">
          {evidence.map(({ citation, claimId, view }) => (
            <CitationEntry
              backHref={`#${claimId}`}
              backLabel={text.facts.back}
              citation={view}
              key={view.id}
              showFullLabel={copy.source.excerpts.showFull}
              sourceHref={`${base}/sources/${citation.source_id}`}
              sourceLinkLabel={text.facts.openSource}
            />
          ))}
        </ol>
      </aside>
    </div>
  );
}
