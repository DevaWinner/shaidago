import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { PageState } from "@/components/project/page-state";
import { SourceView } from "@/components/project/source-view";
import { SiteShell } from "@/components/shell/site-shell";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";
import { loadSource } from "@/lib/api/public-data";
import { createFormatters } from "@/lib/format/formatters";
import { isProjectSlug, isUuid } from "@/lib/identifiers";

type Properties = Readonly<{
  params: Promise<{ locale: string; slug: string; sourceId: string }>;
}>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale, slug, sourceId } = await params;

  if (!isSupportedLocale(locale) || !isProjectSlug(slug) || !isUuid(sourceId)) {
    return {};
  }

  const read = await loadSource(slug, sourceId, locale);

  return read.state === "ok"
    ? { title: read.data.source.title }
    : { robots: { index: false, follow: false } };
}

export default async function SourcePage({ params }: Properties): Promise<ReactNode> {
  const { locale, slug, sourceId } = await params;

  if (!isSupportedLocale(locale) || !isProjectSlug(slug) || !isUuid(sourceId)) {
    notFound();
  }

  setRequestLocale(locale);
  const source = resolveDomain(locale, "source");
  const evidence = resolveDomain(locale, "evidence");
  const read = await loadSource(slug, sourceId, locale);
  const base = `/${locale}/projects/${encodeURIComponent(slug)}`;
  const route = { segments: ["projects", slug, "sources", sourceId] } as const;

  if (read.state === "not_found" || read.state === "invalid_cursor") {
    return (
      <SiteShell locale={locale} route={route}>
        <div lang={source.language}>
          <PageState
            actionHref={base}
            actionLabel={source.messages.notFound.back}
            body={source.messages.notFound.body}
            title={source.messages.notFound.title}
          />
        </div>
      </SiteShell>
    );
  }

  if (read.state === "unavailable") {
    return (
      <SiteShell locale={locale} route={route}>
        <div lang={source.language}>
          <PageState
            actionHref={`${base}/sources/${sourceId}`}
            actionLabel={source.messages.unavailable.retry}
            body={source.messages.unavailable.body}
            title={source.messages.unavailable.title}
          />
        </div>
      </SiteShell>
    );
  }

  return (
    <SiteShell locale={locale} route={route}>
      <div className="grid gap-6" lang={source.language}>
        {source.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <nav aria-label={source.messages.back}>
          <a
            className="inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong"
            href={base}
          >
            {source.messages.back}
          </a>
        </nav>
        <SourceView
          base={base}
          copy={source.messages}
          evidence={evidence.messages}
          format={createFormatters(source.language)}
          source={read.data}
        />
      </div>
    </SiteShell>
  );
}
