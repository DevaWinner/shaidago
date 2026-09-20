import type { ReactNode } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpenText,
  ClipboardCheck,
  CheckCircle2,
  FilePenLine,
  MapPin,
  Search,
  Tags
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import type { Messages } from "@/i18n/catalogue";
import type { Locality, ProjectSummary } from "@/lib/api/public-data";
import { directoryHref } from "@/lib/directory/filters";
import type { CATEGORIES } from "@/lib/directory/filters";
import type { Formatters } from "@/lib/format/formatters";

const section = "grid gap-5 border-t border-border pt-8";
const heading = "m-0 text-ledger-xl leading-tight";

/** A search that is a plain GET form to the directory, so it works with no JavaScript. */
export function HomeSearch({
  copy,
  locale,
  submitLabel
}: Readonly<{ copy: Messages["home"]["search"]; locale: string; submitLabel: string }>): ReactNode {
  return (
    <form action={`/${locale}/projects#results`} className="grid gap-4" method="get" role="search">
      <Field controlId="home-q" description={copy.help} label={copy.label}>
        <Input autoComplete="off" enterKeyHint="search" maxLength={100} name="q" type="search" />
      </Field>
      <Button className="justify-self-start" type="submit">
        <Search aria-hidden="true" className="size-4" />
        {submitLabel}
      </Button>
    </form>
  );
}

/** The newest public record, or an honest sentence when none can be shown. Nothing is invented. */
export function LatestRecord({
  copy,
  directory,
  format,
  locale,
  locality,
  project,
  state
}: Readonly<{
  copy: Messages["home"]["latest"];
  directory: Messages["directory"];
  format: Formatters;
  locale: string;
  locality: Locality | undefined;
  project: ProjectSummary | undefined;
  state: "ok" | "unavailable";
}>): ReactNode {
  return (
    <section aria-labelledby="latest-heading" className={section} data-slot="latest-record">
      <h2 className={heading} id="latest-heading">
        {copy.heading}
      </h2>
      {state === "unavailable" ? (
        <p className="m-0 max-w-[68ch]">{copy.unavailable}</p>
      ) : project === undefined ? (
        <p className="m-0 max-w-[68ch]">{copy.empty}</p>
      ) : (
        <article className="grid gap-5 border border-border bg-card p-5 sm:p-7 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <div className="grid gap-3">
            <h3 className="m-0 text-ledger-xl leading-tight" lang={project.text.served_locale}>
              <a
                className="text-foreground underline underline-offset-4"
                href={`/${locale}/projects/${encodeURIComponent(project.slug)}`}
              >
                {project.text.title}
              </a>
            </h3>
            <p className="m-0 max-w-[68ch] text-muted-foreground" lang={project.text.served_locale}>
              {project.text.summary}
            </p>
            <dl className="m-0 grid gap-3 text-sm sm:grid-cols-3 [&_dd]:m-0 [&_dd]:font-semibold [&_dt]:text-muted-foreground">
              <div>
                <dt>{directory.form.locality}</dt>
                <dd>{locality?.name ?? project.locality_slug}</dd>
              </div>
              <div>
                <dt>{copy.recordedStatus}</dt>
                <dd>{directory.statuses[project.public_status]}</dd>
              </div>
              <div>
                <dt>{copy.lastChecked}</dt>
                <dd>
                  {project.last_checked_on === null ? (
                    copy.notChecked
                  ) : (
                    <time dateTime={project.last_checked_on}>
                      {format.date(project.last_checked_on)}
                    </time>
                  )}
                </dd>
              </div>
            </dl>
          </div>
          <a
            className="inline-flex min-h-11 items-center gap-2 justify-self-start font-semibold text-ledger-accent-strong underline underline-offset-4"
            href={`/${locale}/projects/${encodeURIComponent(project.slug)}`}
          >
            {copy.view}
            <ArrowUpRight aria-hidden="true" className="size-4" />
          </a>
        </article>
      )}
    </section>
  );
}

/** Entry points built only from what the API returned: real localities, and categories with records. */
export function EntryPoints({
  categories,
  copy,
  directory,
  localities,
  locale
}: Readonly<{
  categories: readonly (typeof CATEGORIES)[number][];
  copy: Messages["home"];
  directory: Messages["directory"];
  localities: readonly Locality[];
  locale: string;
}>): ReactNode {
  const councils = localities.filter((item) => item.kind === "area_council");
  const link =
    "inline-flex min-h-11 items-center gap-2 rounded-ledger-control border border-input bg-card px-4 py-2 font-semibold text-foreground no-underline [overflow-wrap:anywhere] hover:bg-[var(--state-selected-background)]";

  if (councils.length === 0 && categories.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      {councils.length === 0 ? null : (
        <section aria-labelledby="localities-heading" className={section}>
          <div className="flex items-center gap-3">
            <MapPin aria-hidden="true" className="size-6 text-primary" strokeWidth={1.8} />
            <h2 className={heading} id="localities-heading">
              {copy.localities.heading}
            </h2>
          </div>
          <ul className="m-0 flex list-none flex-wrap gap-3 p-0">
            {councils.map((item) => (
              <li key={item.slug}>
                <a
                  className={link}
                  href={directoryHref(locale, { locality: item.slug }, { withResults: true })}
                >
                  <MapPin aria-hidden="true" className="size-4" />
                  {item.name}
                </a>
              </li>
            ))}
            <li>
              <a className={link} href={directoryHref(locale, {}, { withResults: true })}>
                {copy.localities.all}
                <ArrowRight aria-hidden="true" className="size-4" />
              </a>
            </li>
          </ul>
        </section>
      )}
      {categories.length === 0 ? null : (
        <section aria-labelledby="categories-heading" className={section}>
          <div className="flex items-center gap-3">
            <Tags aria-hidden="true" className="size-6 text-primary" strokeWidth={1.8} />
            <h2 className={heading} id="categories-heading">
              {copy.categories.heading}
            </h2>
          </div>
          <ul className="m-0 flex list-none flex-wrap gap-3 p-0">
            {categories.map((category) => (
              <li key={category}>
                <a
                  className={link}
                  href={directoryHref(locale, { category }, { withResults: true })}
                >
                  {directory.categories[category]}
                </a>
              </li>
            ))}
          </ul>
          <p className="m-0 text-sm text-muted-foreground">{copy.categories.note}</p>
        </section>
      )}
    </div>
  );
}

export function TrustAndSteps({
  copy,
  locale
}: Readonly<{ copy: Messages["home"]; locale: string }>): ReactNode {
  return (
    <>
      <section
        aria-labelledby="trust-heading"
        className="grid gap-6 border-y border-border py-8 md:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]"
      >
        <div className="grid content-start gap-4">
          <h2 className={heading} id="trust-heading">
            {copy.trust.heading}
          </h2>
          <a
            className="inline-flex min-h-11 items-center gap-2 justify-self-start font-semibold text-ledger-accent-strong underline underline-offset-4"
            href={`/${locale}/trust`}
          >
            {copy.trust.link}
            <ArrowRight aria-hidden="true" className="size-4" />
          </a>
        </div>
        <ul className="m-0 grid list-none gap-4 p-0">
          {[copy.trust.sources, copy.trust.review, copy.trust.privacy].map((item) => (
            <li className="flex items-start gap-3" key={item}>
              <CheckCircle2 aria-hidden="true" className="mt-0.5 size-5 flex-none text-primary" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </section>
      <section aria-labelledby="how-heading" className={section}>
        <h2 className={heading} id="how-heading">
          {copy.how.heading}
        </h2>
        <ol className="m-0 grid list-none gap-6 p-0 md:grid-cols-3">
          {[
            { copy: copy.how.read, icon: BookOpenText },
            { copy: copy.how.report, icon: FilePenLine },
            { copy: copy.how.review, icon: ClipboardCheck }
          ].map((step, index) => {
            const StepIcon = step.icon;
            return (
              <li
                className="grid content-start gap-3 border-t-2 border-foreground pt-4"
                key={step.copy.title}
              >
                <div className="flex items-center justify-between gap-3">
                  <StepIcon aria-hidden="true" className="size-5 text-primary" />
                  <span
                    aria-hidden="true"
                    className="font-ledger-documentary text-sm text-muted-foreground"
                  >
                    0{index + 1}
                  </span>
                </div>
                <h3 className="m-0 text-ledger-lg">{step.copy.title}</h3>
                <p className="m-0">{step.copy.body}</p>
              </li>
            );
          })}
        </ol>
        <p className="m-0 max-w-[68ch] text-sm text-muted-foreground">{copy.limitation}</p>
      </section>
    </>
  );
}
