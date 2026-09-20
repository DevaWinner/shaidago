import type { ReactNode } from "react";

import { Callout, StatusLabel, type StatusTone } from "@/components/ui/feedback";
import { ButtonLink, Link } from "@/components/ui/button";
import { formatMessage, type Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { components } from "@/lib/api/generated/schema";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters, type Formatters } from "@/lib/format/formatters";
import { describeSize } from "@/lib/reviewer/file-size";

type Report = components["schemas"]["ReportDetailOut"];
type Copy = Messages["reviewer"]["detail"];
type QueueCopy = Messages["reviewer"]["queue"];

export type DetailContext = Readonly<{
  copy: Copy;
  queue: QueueCopy;
  format: Formatters;
  language: ApiLocale;
  locale: ApiLocale;
}>;

const lookup = (table: object, key: string): string =>
  (table as Readonly<Record<string, string | undefined>>)[key] ?? key;

const RISK_TONE: Readonly<Record<string, StatusTone>> = {
  high: "problem",
  elevated: "limited-evidence",
  standard: "unavailable"
};

export function Section({
  children,
  id,
  title
}: Readonly<{ children: ReactNode; id: string; title: string }>): ReactNode {
  return (
    <section
      aria-labelledby={`${id}-heading`}
      className="grid gap-3 border-t-2 border-border pt-4"
      data-section={id}
      id={id}
    >
      <h2 className="m-0 text-ledger-lg" id={`${id}-heading`}>
        {title}
      </h2>
      {children}
    </section>
  );
}

export function DemoWarning({ copy }: Readonly<{ copy: Copy }>): ReactNode {
  return (
    <Callout title={copy.demo.title} tone="warning">
      {copy.demo.body}
    </Callout>
  );
}

/** Status and risk come first, in words, with the dates a reviewer needs to judge how stale it is. */
export function ReportHeader({
  report,
  context
}: Readonly<{ report: Report; context: DetailContext }>): ReactNode {
  const { copy, queue, format } = context;

  return (
    <div className="grid gap-3" data-slot="report-header">
      <div className="flex flex-wrap items-center gap-2">
        <StatusLabel tone="under-review">
          {copy.header.status}: {lookup(queue.statuses, report.status)}
        </StatusLabel>
        <StatusLabel tone={RISK_TONE[report.risk_level] ?? "unavailable"}>
          {copy.header.risk}: {lookup(queue.risks, report.risk_level)}
        </StatusLabel>
      </div>
      <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-sm">
        <li>
          {formatMessageLite(copy.header.received, { date: format.dateTime(report.created_at) })}
        </li>
        <li>
          {formatMessageLite(copy.header.updated, {
            date: format.dateTime(report.status_updated_at)
          })}
        </li>
        <li>{formatMessageLite(copy.header.version, { version: report.version })}</li>
      </ul>
    </div>
  );
}

export function ObservationSection({
  report,
  context
}: Readonly<{ report: Report; context: DetailContext }>): ReactNode {
  const { copy, queue, locale } = context;

  return (
    <Section id="observation" title={copy.sections.observation}>
      <dl className="m-0 grid gap-2">
        <div>
          <dt className="font-semibold">{copy.observation.category}</dt>
          <dd className="m-0">{lookup(queue.categories, report.concern_category)}</dd>
        </div>
        <div>
          <dt className="font-semibold">{copy.observation.project}</dt>
          <dd className="m-0 flex flex-wrap items-center gap-2">
            <span className="[overflow-wrap:anywhere]">{report.project_slug}</span>
            <Link href={`/${locale}/projects/${encodeURIComponent(report.project_slug)}`}>
              {copy.header.publicRecord}
            </Link>
          </dd>
        </div>
      </dl>
      <div className="grid gap-1">
        <h3 className="m-0 text-base">{copy.observation.description}</h3>
        {/* Plain text only: React escapes it, and it is never treated as markup or a link. */}
        <p
          className="m-0 max-w-[68ch] whitespace-pre-wrap border-s-[0.375rem] border-border ps-3 [overflow-wrap:anywhere]"
          data-slot="report-description"
        >
          {report.description}
        </p>
        <small className="text-muted-foreground">{copy.observation.descriptionNote}</small>
      </div>
    </Section>
  );
}

/** The list of files. `renderDownload` lets the download control be a client island. */
export function EvidenceSection({
  report,
  context,
  renderDownload
}: Readonly<{
  report: Report;
  context: DetailContext;
  renderDownload: (evidence: Report["evidence"][number]) => ReactNode;
}>): ReactNode {
  const { copy, format, language } = context;
  const words = copy.evidence;
  const plural = (template: string, count: number): string =>
    formatMessage(language, template, { count });

  return (
    <Section id="evidence" title={copy.sections.evidence}>
      {report.evidence.length === 0 ? (
        <p className="m-0">{words.empty}</p>
      ) : (
        <>
          <p className="m-0 text-sm text-muted-foreground">{words.note}</p>
          <ul className="m-0 grid list-none gap-3 p-0" data-slot="evidence-list">
            {report.evidence.map((file) => (
              <li className="grid gap-2 border border-border bg-card p-3" key={file.evidence_id}>
                <strong className="[overflow-wrap:anywhere]">{file.display_name}</strong>
                <dl className="m-0 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="inline font-semibold">{words.type}: </dt>
                    <dd className="m-0 inline [overflow-wrap:anywhere]">{file.mime_type}</dd>
                  </div>
                  <div>
                    <dt className="inline font-semibold">{words.size}: </dt>
                    <dd className="m-0 inline">
                      {describeSize(file.size_bytes, words, format, plural)}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline font-semibold">{words.sanitation}: </dt>
                    <dd className="m-0 inline">
                      {lookup(words.sanitationStates, file.sanitation_state)}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline font-semibold">{words.scan}: </dt>
                    <dd className="m-0 inline">{lookup(words.scanStates, file.scan_state)}</dd>
                  </div>
                </dl>
                {file.scan_state === "not_scanned_demo" ? (
                  <Callout title={lookup(words.scanStates, file.scan_state)} tone="warning">
                    {words.demoLimit}
                  </Callout>
                ) : null}
                <small className="text-muted-foreground">
                  {formatMessageLite(words.added, { date: format.dateTime(file.created_at) })}
                </small>
                {renderDownload(file)}
              </li>
            ))}
          </ul>
        </>
      )}
    </Section>
  );
}

export type ContactOutcome = "not_requested" | "shown" | "denied" | "unavailable";

/**
 * Contact stays hidden until an explicit action. Revealing is a plain GET form (`reveal=contact`),
 * so it needs no script; the API records each reveal in its audit log before returning the value,
 * and nothing about the value is ever placed in the address.
 */
export function ContactSection({
  report,
  context,
  outcome,
  revealHref,
  hideHref
}: Readonly<{
  report: Report;
  context: DetailContext;
  outcome: ContactOutcome;
  revealHref: string;
  hideHref: string;
}>): ReactNode {
  const words = context.copy.contact;
  const shown = outcome === "shown" && report.contact !== null;

  return (
    <Section id="contact" title={context.copy.sections.contact}>
      {!report.has_contact ? (
        <p className="m-0">{words.none}</p>
      ) : shown ? (
        <div className="grid gap-2" data-slot="contact-revealed">
          <p className="m-0 [overflow-wrap:anywhere]">
            {formatMessageLite(words.shown, {
              channel: report.contact?.channel ?? "",
              value: report.contact?.value ?? ""
            })}
          </p>
          <small className="text-muted-foreground">{words.auditNote}</small>
          <div>
            <ButtonLink href={hideHref} variant="secondary">
              {words.hide}
            </ButtonLink>
          </div>
        </div>
      ) : (
        <div className="grid gap-2">
          <p className="m-0">{words.hidden}</p>
          {outcome === "denied" ? (
            <p className="m-0 font-semibold" role="status">
              {words.denied}
            </p>
          ) : outcome === "unavailable" || outcome === "shown" ? (
            <p className="m-0 font-semibold" role="status">
              {words.unavailable}
            </p>
          ) : null}
          <small className="text-muted-foreground">{words.revealNote}</small>
          <form action={revealHref} method="get">
            <input name="reveal" type="hidden" value="contact" />
            <button
              className="inline-flex min-h-11 cursor-pointer items-center rounded-ledger-control border border-foreground bg-card px-3 py-2 font-semibold"
              type="submit"
            >
              {words.reveal}
            </button>
          </form>
        </div>
      )}
    </Section>
  );
}

export function HistorySection({
  report,
  context
}: Readonly<{ report: Report; context: DetailContext }>): ReactNode {
  const { copy, queue, format } = context;
  const words = copy.history;
  const events = [...report.events].sort((left, right) =>
    right.occurred_at.localeCompare(left.occurred_at)
  );

  return (
    <Section id="history" title={copy.sections.history}>
      {events.length === 0 ? (
        <p className="m-0">{words.empty}</p>
      ) : (
        <ol className="m-0 grid list-none gap-3 p-0" data-slot="history-list">
          {events.map((event) => (
            <li className="grid gap-1 border-s-[0.375rem] border-border ps-3" key={event.event_id}>
              <strong>
                {event.previous_status === null
                  ? formatMessageLite(words.first, { to: lookup(queue.statuses, event.new_status) })
                  : formatMessageLite(words.from, {
                      from: lookup(queue.statuses, event.previous_status),
                      to: lookup(queue.statuses, event.new_status)
                    })}
              </strong>
              <small>
                <time dateTime={event.occurred_at}>{format.dateTime(event.occurred_at)}</time>
                {" · "}
                {formatMessageLite(words.actor, { actor: lookup(words.actors, event.actor_type) })}
              </small>
              <p className="m-0 text-sm [overflow-wrap:anywhere]">
                <strong>{words.shownToReporter}:</strong>{" "}
                {event.public_message === "" ? words.noMessage : event.public_message}
              </p>
              {event.internal_reason === null || event.internal_reason === "" ? null : (
                <p className="m-0 text-sm [overflow-wrap:anywhere]">
                  <strong>{words.internal}:</strong> {event.internal_reason}
                </p>
              )}
            </li>
          ))}
        </ol>
      )}
    </Section>
  );
}

/** Read-only view of the questions; asking and withdrawing are added by the notes task. */
export function QuestionsList({
  report,
  context,
  renderActions
}: Readonly<{
  report: Report;
  context: DetailContext;
  /** Extra controls for a question that is still open, such as withdrawing it. */
  renderActions?: (item: Report["follow_ups"][number]) => ReactNode;
}>): ReactNode {
  const { copy, format } = context;
  const words = copy.questions;

  return report.follow_ups.length === 0 ? (
    <p className="m-0">{words.empty}</p>
  ) : (
    <ul className="m-0 grid list-none gap-3 p-0" data-slot="question-list">
      {report.follow_ups.map((item) => (
        <li className="grid gap-1 border border-border bg-card p-3" key={item.question_id}>
          <strong className="[overflow-wrap:anywhere]">{item.question}</strong>
          <small>{formatMessageLite(words.asked, { date: format.dateTime(item.asked_at) })}</small>
          {item.withdrawn ? (
            <small className="font-semibold">{words.withdrawn}</small>
          ) : item.answer_kind === null ? (
            <small>{words.noAnswer}</small>
          ) : (
            <p className="m-0 text-sm [overflow-wrap:anywhere]">
              <strong>
                {formatMessageLite(words.answered, { kind: lookup(words.kinds, item.answer_kind) })}
                :
              </strong>{" "}
              {item.answer ?? words.private}
            </p>
          )}
          {item.withdrawn || item.answer_kind !== null ? null : renderActions?.(item)}
        </li>
      ))}
    </ul>
  );
}

export type NotesView =
  | Readonly<{
      state: "ok";
      items: readonly components["schemas"]["NoteOut"][];
      nextHref: string | undefined;
      firstHref: string | undefined;
    }>
  | Readonly<{ state: "unavailable"; retryHref: string }>;

/** Internal notes, oldest first, as private plain text with the form supplied by the caller. */
export function NotesSection({
  context,
  form,
  notes,
  words
}: Readonly<{
  context: DetailContext;
  form: ReactNode;
  notes: NotesView;
  words: Messages["reviewer"]["notes"];
}>): ReactNode {
  const { copy, format } = context;

  return (
    <Section id="notes" title={copy.sections.notes}>
      <p className="m-0 text-sm text-muted-foreground">{words.intro}</p>
      {notes.state === "unavailable" ? (
        <div className="grid gap-2 border-2 border-border bg-card p-3" role="status">
          <p className="m-0">{words.unavailable}</p>
          <p className="m-0">
            <Link href={notes.retryHref}>{words.retry}</Link>
          </p>
        </div>
      ) : notes.items.length === 0 ? (
        <p className="m-0">{words.empty}</p>
      ) : (
        <>
          <ol className="m-0 grid list-none gap-3 p-0" data-slot="notes-list">
            {notes.items.map((note) => (
              <li className="grid gap-1 border-s-[0.375rem] border-border ps-3" key={note.note_id}>
                <small>
                  <time dateTime={note.created_at}>{format.dateTime(note.created_at)}</time>
                  {note.author === null
                    ? null
                    : ` · ${formatMessageLite(words.by, { author: note.author })}`}
                </small>
                {/* Plain text only: escaped by React, never treated as markup. */}
                <p className="m-0 max-w-[68ch] whitespace-pre-wrap [overflow-wrap:anywhere]">
                  {note.body ?? words.gone}
                </p>
              </li>
            ))}
          </ol>
          {notes.nextHref === undefined && notes.firstHref === undefined ? null : (
            <nav aria-label={words.navLabel} className="flex flex-wrap gap-3">
              {notes.firstHref === undefined ? null : (
                <ButtonLink href={notes.firstHref} variant="secondary">
                  {words.first}
                </ButtonLink>
              )}
              {notes.nextHref === undefined ? null : (
                <ButtonLink href={notes.nextHref} rel="next" variant="secondary">
                  {words.more}
                </ButtonLink>
              )}
            </nav>
          )}
        </>
      )}
      {form}
    </Section>
  );
}

export function HandleSection({
  report,
  context
}: Readonly<{ report: Report; context: DetailContext }>): ReactNode {
  const words = context.copy.handle;
  const record = report.track_record;

  return (
    <Section id="handle" title={context.copy.sections.handle}>
      {record === null ? (
        <p className="m-0">{words.none}</p>
      ) : (
        <>
          <p className="m-0 font-semibold">{words.note}</p>
          <dl className="m-0 grid gap-1 text-sm">
            <div>
              <dt className="inline font-semibold">{words.name}: </dt>
              <dd className="m-0 inline [overflow-wrap:anywhere]">{record.handle}</dd>
            </div>
            <div>
              <dt className="inline font-semibold">{words.total}: </dt>
              <dd className="m-0 inline">{record.reports_total}</dd>
            </div>
            <div>
              <dt className="inline font-semibold">{words.verified}: </dt>
              <dd className="m-0 inline">{record.verified_for_public_update}</dd>
            </div>
            <div>
              <dt className="inline font-semibold">{words.closed}: </dt>
              <dd className="m-0 inline">{record.closed}</dd>
            </div>
          </dl>
        </>
      )}
    </Section>
  );
}

export function ScoutSection({ context }: Readonly<{ context: DetailContext }>): ReactNode {
  const words = context.copy.scout;

  return (
    <Section id="scout" title={context.copy.sections.scout}>
      <p className="m-0">{words.body}</p>
      <small className="text-muted-foreground">{words.private}</small>
    </Section>
  );
}

export function detailContext(
  copy: Copy,
  queue: QueueCopy,
  language: ApiLocale,
  locale: ApiLocale
): DetailContext {
  return { copy, queue, format: createFormatters(language), language, locale };
}
