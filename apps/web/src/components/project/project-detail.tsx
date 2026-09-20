import type { ReactNode } from "react";

import { CitationEntry, DateGroup, EvidenceGap } from "@/components/evidence/evidence";
import {
  PublicUpdateEntry,
  StatementClaim,
  citationView,
  type EntryCopy
} from "@/components/project/update-entry";
import { ButtonLink } from "@/components/ui/button";
import { formatMessage } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { ProjectDetail } from "@/lib/api/public-data";
import { STALE_AFTER_DAYS, isStale } from "@/lib/directory/freshness";
import { formatMessageLite } from "@/lib/directory/format-lite";
import type { Formatters } from "@/lib/format/formatters";

type Copy = EntryCopy;

type FactOrUpdate = ProjectDetail["facts"][number] | ProjectDetail["updates"][number];

const section = "grid gap-4 border-t border-border pt-8";
const heading = "m-0 text-ledger-xl leading-tight";

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
  project,
  questionPanel
}: Readonly<{
  copy: Copy;
  format: Formatters;
  language: ApiLocale;
  localityName: string;
  locale: string;
  now: Date;
  project: ProjectDetail;
  /** The client-enhanced question island, supplied by the page so this view stays server-rendered. */
  questionPanel?: ReactNode;
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

  const claim = (statement: FactOrUpdate, claimId: string): ReactNode => (
    <StatementClaim claimId={claimId} copy={copy} language={language} statement={statement} />
  );

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
                <PublicUpdateEntry
                  claimId={`update-${update.id}`}
                  copy={copy}
                  format={format}
                  key={update.id}
                  language={language}
                  now={now}
                  update={update}
                />
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
          {questionPanel}
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
