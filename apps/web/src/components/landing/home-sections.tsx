import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import type { Messages } from "@/i18n/catalogue";
import type { Locality, ProjectSummary } from "@/lib/api/public-data";
import { directoryHref } from "@/lib/directory/filters";
import type { CATEGORIES } from "@/lib/directory/filters";
import type { Formatters } from "@/lib/format/formatters";

const section = "grid gap-4 border-t border-border pt-8";
const heading = "m-0 text-ledger-xl leading-tight";

/** A search that is a plain GET form to the directory, so it works with no JavaScript. */
export function HomeSearch({
  copy,
  locale,
  submitLabel
}: Readonly<{ copy: Messages["home"]["search"]; locale: string; submitLabel: string }>): ReactNode {
  return (
    <form
      action={`/${locale}/projects#results`}
      className="grid max-w-[60ch] gap-3"
      method="get"
      role="search"
    >
      <Field controlId="home-q" description={copy.help} label={copy.label}>
        <Input autoComplete="off" enterKeyHint="search" maxLength={100} name="q" type="search" />
      </Field>
      <div>
        <Button type="submit">{submitLabel}</Button>
      </div>
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
        <article className="grid gap-2 border border-border border-s-[0.375rem] border-s-primary bg-card p-4 sm:p-6">
          <h3 className="m-0 text-ledger-lg leading-tight" lang={project.text.served_locale}>
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
          <dl className="m-0 flex flex-wrap gap-x-6 gap-y-1 text-sm [&_dd]:m-0 [&_dd]:font-semibold [&_dt]:text-muted-foreground">
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
    "inline-flex min-h-11 items-center rounded-ledger-control border border-foreground bg-card px-4 py-2 font-semibold text-foreground no-underline [overflow-wrap:anywhere]";

  return (
    <>
      {councils.length === 0 ? null : (
        <section aria-labelledby="localities-heading" className={section}>
          <h2 className={heading} id="localities-heading">
            {copy.localities.heading}
          </h2>
          <ul className="m-0 flex list-none flex-wrap gap-3 p-0">
            {councils.map((item) => (
              <li key={item.slug}>
                <a
                  className={link}
                  href={directoryHref(locale, { locality: item.slug }, { withResults: true })}
                >
                  {item.name}
                </a>
              </li>
            ))}
            <li>
              <a className={link} href={directoryHref(locale, {}, { withResults: true })}>
                {copy.localities.all}
              </a>
            </li>
          </ul>
        </section>
      )}
      {categories.length === 0 ? null : (
        <section aria-labelledby="categories-heading" className={section}>
          <h2 className={heading} id="categories-heading">
            {copy.categories.heading}
          </h2>
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
    </>
  );
}

export function TrustAndSteps({
  copy,
  locale
}: Readonly<{ copy: Messages["home"]; locale: string }>): ReactNode {
  return (
    <>
      <section aria-labelledby="trust-heading" className={section}>
        <h2 className={heading} id="trust-heading">
          {copy.trust.heading}
        </h2>
        <ul className="m-0 grid max-w-[68ch] list-disc gap-2 ps-5">
          <li>{copy.trust.sources}</li>
          <li>{copy.trust.review}</li>
          <li>{copy.trust.privacy}</li>
        </ul>
        <p className="m-0">
          <a
            className="font-semibold text-ledger-accent-strong underline"
            href={`/${locale}/trust`}
          >
            {copy.trust.link}
          </a>
        </p>
      </section>
      <section aria-labelledby="how-heading" className={section}>
        <h2 className={heading} id="how-heading">
          {copy.how.heading}
        </h2>
        <ol className="m-0 grid list-none gap-4 p-0 md:grid-cols-3">
          {[copy.how.read, copy.how.report, copy.how.review].map((step) => (
            <li
              className="grid content-start gap-1 border-t-2 border-foreground pt-3"
              key={step.title}
            >
              <h3 className="m-0 text-ledger-lg">{step.title}</h3>
              <p className="m-0">{step.body}</p>
            </li>
          ))}
        </ol>
        <p className="m-0 max-w-[68ch] text-sm text-muted-foreground">{copy.limitation}</p>
      </section>
    </>
  );
}
