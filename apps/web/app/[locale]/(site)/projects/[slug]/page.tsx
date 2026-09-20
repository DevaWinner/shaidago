import type { Metadata, Route } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { ProjectQuestion } from "@/components/project/project-question";
import { PageState } from "@/components/project/page-state";
import { ProjectDetailView } from "@/components/project/project-detail";
import { SiteShell } from "@/components/shell/site-shell";
import { resolveDomain } from "@/i18n/catalogue";
import { LOCALES, isSupportedLocale } from "@/i18n/routing";
import { loadLocalities, loadProject } from "@/lib/api/public-data";
import { createFormatters } from "@/lib/format/formatters";
import { isProjectSlug } from "@/lib/identifiers";

// Rendered per request; the API is never called during a build. No `force-dynamic` (it would turn
// the tagged public cache off).

type Properties = Readonly<{ params: Promise<{ locale: string; slug: string }> }>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale, slug } = await params;

  if (!isSupportedLocale(locale) || !isProjectSlug(slug)) {
    return {};
  }

  const read = await loadProject(slug, locale);

  if (read.state !== "ok") {
    return { robots: { index: false, follow: false } };
  }

  const path = (code: string): string => `/${code}/projects/${encodeURIComponent(slug)}`;

  return {
    title: read.data.text.title,
    description: read.data.text.summary,
    alternates: {
      canonical: path(locale),
      languages: Object.fromEntries(LOCALES.map((code) => [code, path(code)]))
    }
  };
}

export default async function ProjectPage({ params }: Properties): Promise<ReactNode> {
  const { locale, slug } = await params;

  if (!isSupportedLocale(locale) || !isProjectSlug(slug)) {
    notFound();
  }

  setRequestLocale(locale);
  const project = resolveDomain(locale, "project");
  const directory = resolveDomain(locale, "directory");
  const evidence = resolveDomain(locale, "evidence");
  const source = resolveDomain(locale, "source");
  const qa = resolveDomain(locale, "qa");
  const problems = resolveDomain(locale, "problems");
  const [read, localityRead] = await Promise.all([
    loadProject(slug, locale),
    loadLocalities(locale)
  ]);

  if (read.state === "not_found" || read.state === "invalid_cursor") {
    notFound();
  }

  const shell = { segments: ["projects", slug] } as const;
  const directoryHref = `/${locale}/projects` as Route;

  if (read.state === "unavailable") {
    return (
      <SiteShell locale={locale} route={shell}>
        <div lang={project.language}>
          <PageState
            actionHref={`/${locale}/projects/${encodeURIComponent(slug)}`}
            actionLabel={project.messages.unavailable.retry}
            body={project.messages.unavailable.body}
            title={project.messages.unavailable.title}
          />
        </div>
      </SiteShell>
    );
  }

  const localities = localityRead.state === "ok" ? localityRead.data : [];
  const localityName =
    localities.find((item) => item.slug === read.data.locality_slug)?.name ??
    read.data.locality_slug;
  const format = createFormatters(project.language);

  return (
    <SiteShell locale={locale} route={shell}>
      <div className="grid gap-6" lang={project.language}>
        {project.isOriginal || directory.isOriginal || source.isOriginal || qa.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <nav aria-label={project.messages.breadcrumb.label}>
          <a
            className="inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong"
            href={directoryHref}
          >
            {project.messages.breadcrumb.directory}
          </a>
        </nav>
        <ProjectDetailView
          copy={{
            directory: directory.messages,
            evidence: evidence.messages,
            project: project.messages,
            source: source.messages
          }}
          format={format}
          language={project.language}
          locale={locale}
          localityName={localityName}
          now={new Date()}
          project={read.data}
          questionPanel={
            <div lang={qa.language}>
              <ProjectQuestion
                base={`/${locale}/projects/${encodeURIComponent(slug)}`}
                copy={qa.messages}
                evidence={evidence.messages}
                factsHref="#facts-heading"
                language={qa.language}
                locale={locale}
                problems={problems.messages}
                reportHref={`/${locale}/report?project=${encodeURIComponent(slug)}`}
                slug={slug}
              />
            </div>
          }
        />
      </div>
    </SiteShell>
  );
}
