import type { Metadata, Route } from "next";
import { notFound, redirect } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";
import { LibraryBig } from "lucide-react";

import { DirectoryForm } from "@/components/directory/directory-form";
import { DirectoryResults } from "@/components/directory/directory-results";
import { FilterPills } from "@/components/directory/filter-pills";
import { FocusResults } from "@/components/directory/focus-results";
import { TranslationNotice } from "@/components/evidence/evidence";
import { SiteShell } from "@/components/shell/site-shell";
import { PageHeader } from "@/components/ui/page-header";
import { resolveDomain } from "@/i18n/catalogue";
import { LOCALES, isSupportedLocale } from "@/i18n/routing";
import { loadLocalities, loadProjectPage } from "@/lib/api/public-data";
import {
  FILTER_NAMES,
  directoryHref,
  parseFilters,
  type RawSearchParams
} from "@/lib/directory/filters";
import { createFormatters } from "@/lib/format/formatters";

// Rendered per request because the filters are read from the URL (`searchParams`), and the API is
// never called during a build. Do not add `dynamic = "force-dynamic"`: it also forces every fetch to
// no-store, which would silently disable the tagged public data cache (FE-063).

type ProjectsProperties = Readonly<{
  params: Promise<{ locale: string }>;
  searchParams: Promise<RawSearchParams>;
}>;

export async function generateMetadata({
  params,
  searchParams
}: ProjectsProperties): Promise<Metadata> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    return {};
  }

  const copy = resolveDomain(locale, "directory").messages;
  const raw = await searchParams;
  const { filters } = parseFilters(raw, []);
  // Free-text searches are not indexed; the canonical URL never carries a cursor.

  return {
    title: copy.title,
    description: copy.intro,
    alternates: {
      canonical: directoryHref(locale, filters),
      languages: Object.fromEntries(LOCALES.map((code) => [code, directoryHref(code, filters)]))
    },
    robots: filters.q === undefined ? { index: true, follow: true } : { index: false, follow: true }
  };
}

export default async function ProjectsPage({
  params,
  searchParams
}: ProjectsProperties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const raw = await searchParams;
  const directory = resolveDomain(locale, "directory");
  const evidence = resolveDomain(locale, "evidence");
  const localityRead = await loadLocalities(locale);
  const localities = localityRead.state === "ok" ? localityRead.data : [];
  const { filters, needsCanonicalRedirect } = parseFilters(
    raw,
    localities.map((item) => item.slug)
  );

  // A plain form always submits empty fields, so the redirect cleans the URL and re-adds the results
  // anchor that a GET submission drops. Only redirect when the locality list is known: without it a valid shared locality would be dropped.
  if (needsCanonicalRedirect && localityRead.state === "ok") {
    // Built from allowlisted, encoded parts only; a dynamic query string is not in the typed route table.
    redirect(directoryHref(locale, filters, { cursor: true, withResults: true }) as Route);
  }

  const read = await loadProjectPage(filters, locale);
  const format = createFormatters(directory.language);

  return (
    <SiteShell
      locale={locale}
      route={{ segments: ["projects"], keep: FILTER_NAMES, search: filters }}
    >
      <div className="grid gap-6" lang={directory.language}>
        {directory.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <PageHeader
          icon={LibraryBig}
          intro={<p>{directory.messages.intro}</p>}
          title={directory.messages.title}
        />
        <DirectoryForm
          copy={directory.messages}
          evidence={evidence.messages}
          filters={filters}
          localities={localities}
          locale={locale}
        />
        <FilterPills
          copy={directory.messages}
          evidence={evidence.messages}
          filters={filters}
          localities={localities}
          locale={locale}
        />
        <DirectoryResults
          copy={directory.messages}
          evidence={evidence.messages}
          filters={filters}
          format={format}
          language={directory.language}
          localities={localities}
          locale={locale}
          now={new Date()}
          read={read}
        />
        <FocusResults />
      </div>
    </SiteShell>
  );
}
