import type { ReactNode } from "react";

import { Button, ButtonLink } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/field";
import { StatusLabel, type StatusTone } from "@/components/ui/feedback";
import { formatMessage, type Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { components } from "@/lib/api/generated/schema";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters } from "@/lib/format/formatters";
import {
  QUEUE_CATEGORIES,
  QUEUE_RISKS,
  QUEUE_STATUSES,
  type QueueFilters
} from "@/lib/reviewer/queue-filters";

type Copy = Messages["reviewer"]["queue"];
type Item = components["schemas"]["QueueItemOut"];

const RISK_TONE: Readonly<Record<string, StatusTone>> = {
  high: "problem",
  elevated: "limited-evidence",
  standard: "unavailable"
};

/**
 * The filter form is a plain GET form to the queue address, so it works with no JavaScript and the
 * result is a shareable link. It never carries a cursor: a new filter starts at the first page.
 */
export function QueueFilterForm({
  action,
  clearHref,
  copy,
  filters
}: Readonly<{ action: string; clearHref: string; copy: Copy; filters: QueueFilters }>): ReactNode {
  const form = copy.filters;

  return (
    <form
      action={action}
      aria-label={form.label}
      className="grid gap-4 border-y border-border py-4"
      data-slot="queue-filters"
      method="get"
    >
      <div className="grid items-start gap-4 min-[360px]:grid-cols-2 lg:grid-cols-4">
        <Field controlId="queue-status" label={form.status}>
          <Select defaultValue={filters.status ?? ""} name="status">
            <option value="">{form.any}</option>
            {QUEUE_STATUSES.map((value) => (
              <option key={value} value={value}>
                {copy.statuses[value]}
              </option>
            ))}
          </Select>
        </Field>
        <Field controlId="queue-risk" label={form.risk}>
          <Select defaultValue={filters.risk ?? ""} name="risk">
            <option value="">{form.any}</option>
            {QUEUE_RISKS.map((value) => (
              <option key={value} value={value}>
                {copy.risks[value]}
              </option>
            ))}
          </Select>
        </Field>
        <Field controlId="queue-category" label={form.category}>
          <Select defaultValue={filters.category ?? ""} name="category">
            <option value="">{form.any}</option>
            {QUEUE_CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {copy.categories[value]}
              </option>
            ))}
          </Select>
        </Field>
        <Field controlId="queue-project" description={form.projectHelp} label={form.project}>
          <Input
            autoComplete="off"
            defaultValue={filters.project ?? ""}
            maxLength={120}
            name="project"
            pattern="[a-z0-9\-]+"
            type="text"
          />
        </Field>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button type="submit">{form.apply}</Button>
        <ButtonLink href={clearHref} variant="secondary">
          {form.clear}
        </ButtonLink>
      </div>
    </form>
  );
}

function QueueRow({
  copy,
  format,
  language,
  reportHref,
  item
}: Readonly<{
  copy: Copy;
  format: ReturnType<typeof createFormatters>;
  item: Item;
  language: ApiLocale;
  reportHref: string;
}>): ReactNode {
  const words = copy.item;
  const status = (copy.statuses as Readonly<Record<string, string>>)[item.status] ?? item.status;
  const risk = (copy.risks as Readonly<Record<string, string>>)[item.risk_level] ?? item.risk_level;
  const category =
    (copy.categories as Readonly<Record<string, string>>)[item.concern_category] ??
    item.concern_category;
  const received = format.date(item.created_at);

  return (
    <li
      className="grid gap-3 border border-border bg-card p-4"
      data-report-status={item.status}
      data-slot="queue-item"
    >
      <div className="flex flex-wrap items-center gap-2">
        <strong className="text-ledger-lg [overflow-wrap:anywhere]">{item.project_slug}</strong>
        <span>{category}</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <StatusLabel tone="under-review">
          {words.statusLabel}: {status}
        </StatusLabel>
        <StatusLabel tone={RISK_TONE[item.risk_level] ?? "unavailable"}>
          {words.riskLabel}: {risk}
        </StatusLabel>
      </div>
      <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-sm">
        <li>{formatMessageLite(words.received, { date: received })}</li>
        <li>{formatMessageLite(words.updated, { date: format.date(item.status_updated_at) })}</li>
        <li>
          {item.evidence_count === 0
            ? words.noFiles
            : formatMessage(language, words.files, { count: item.evidence_count })}
        </li>
        <li>
          {item.open_follow_ups === 0
            ? words.noQuestions
            : formatMessage(language, words.questions, { count: item.open_follow_ups })}
        </li>
        <li>{item.has_contact ? words.contact : words.noContact}</li>
      </ul>
      <div>
        {/* A plain anchor: the framework link would prefetch a private route. */}
        <ButtonLink
          aria-label={formatMessageLite(words.openLabel, {
            project: item.project_slug,
            date: received
          })}
          href={reportHref}
          variant="secondary"
        >
          {words.open}
        </ButtonLink>
      </div>
    </li>
  );
}

export function QueueList({
  copy,
  items,
  language,
  locale
}: Readonly<{
  copy: Copy;
  items: readonly Item[];
  language: ApiLocale;
  locale: ApiLocale;
}>): ReactNode {
  const format = createFormatters(language);

  return (
    <ol className="m-0 grid list-none gap-3 p-0" data-slot="queue-list">
      {items.map((item) => (
        <QueueRow
          copy={copy}
          format={format}
          item={item}
          key={item.report_id}
          language={language}
          reportHref={`/${locale}/reviewer/reports/${item.report_id}`}
        />
      ))}
    </ol>
  );
}

export function QueueNotice({
  action,
  body,
  title
}: Readonly<{
  action?: ReactNode;
  body: string;
  title: string;
}>): ReactNode {
  return (
    <div
      className="grid gap-2 border-2 border-border bg-card p-4"
      data-slot="queue-notice"
      role="status"
    >
      <h2 className="m-0 text-ledger-lg">{title}</h2>
      <p className="m-0">{body}</p>
      {action}
    </div>
  );
}
