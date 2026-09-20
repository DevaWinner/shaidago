import type { Metadata, Route } from "next";
import { notFound, redirect } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { SiteShell } from "@/components/shell/site-shell";
import { ButtonLink } from "@/components/ui/button";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";
import { loadProjectPage } from "@/lib/api/public-data";
import { isProjectSlug } from "@/lib/identifiers";

type Properties = Readonly<{
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale) ? resolveDomain(locale, "report").messages.title : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

/**
 * The entry to reporting. A report is about one record, so a `?project=` link (from a record page)
 * goes straight to that record's form; without one, the person chooses a record. The chosen slug is
 * validated before it is used in a path, and nothing about a report is read from the address.
 */
export default async function ReportEntryPage({
  params,
  searchParams
}: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const { project } = await searchParams;

  if (typeof project === "string" && isProjectSlug(project)) {
    redirect(`/${locale}/report/${encodeURIComponent(project)}` as Route);
  }

  const report = resolveDomain(locale, "report");
  const evidence = resolveDomain(locale, "evidence");
  const track = resolveDomain(locale, "track");
  const read = await loadProjectPage({}, locale, 12);

  return (
    <SiteShell locale={locale} route={{ segments: ["report"] }}>
      <div className="grid max-w-[68ch] gap-6" lang={report.language}>
        {report.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <h1 className="m-0 text-ledger-display leading-[1.1]">{report.messages.chooser.title}</h1>
        <p className="m-0">{report.messages.chooser.lead}</p>
        {read.state === "ok" && read.data.items.length > 0 ? (
          <section aria-labelledby="records-heading" className="grid gap-3">
            <h2 className="m-0 text-ledger-lg" id="records-heading">
              {report.messages.chooser.listHeading}
            </h2>
            <ul className="m-0 grid list-none gap-1 p-0">
              {read.data.items.map((item) => (
                <li key={item.slug}>
                  <a
                    className="inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong underline"
                    href={`/${locale}/report/${encodeURIComponent(item.slug)}`}
                  >
                    {item.text.title}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ) : (
          <p className="m-0">{report.messages.chooser.unavailable}</p>
        )}
        <div className="flex flex-wrap gap-3">
          <ButtonLink href={`/${locale}/projects`} variant="secondary">
            {report.messages.chooser.browse}
          </ButtonLink>
          <ButtonLink href={`/${locale}/track`} variant="secondary">
            <span lang={track.language}>{track.messages.title}</span>
          </ButtonLink>
        </div>
      </div>
    </SiteShell>
  );
}
