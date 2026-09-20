import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { setRequestLocale } from "next-intl/server";
import { ArrowRight, FileWarning } from "lucide-react";
import type { ReactNode } from "react";

import {
  EntryPoints,
  HomeSearch,
  LatestRecord,
  TrustAndSteps
} from "@/components/landing/home-sections";
import { SiteShell } from "@/components/shell/site-shell";
import { ButtonLink } from "@/components/ui/button";
import { resolveDomain } from "@/i18n/catalogue";
import { localeHref } from "@/i18n/locale-href";
import { LOCALES, isSupportedLocale } from "@/i18n/routing";
import { loadLocalities, loadProjectPage } from "@/lib/api/public-data";
import { CATEGORIES } from "@/lib/directory/filters";
import { createFormatters } from "@/lib/format/formatters";

type LandingProperties = Readonly<{ params: Promise<{ locale: string }> }>;

export async function generateMetadata({ params }: LandingProperties): Promise<Metadata> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    return {};
  }

  const landing = resolveDomain(locale, "landing").messages;

  return {
    // No social preview image: none has been approved, and none is invented.
    description: landing.lead,
    alternates: {
      canonical: `/${locale}`,
      languages: Object.fromEntries(LOCALES.map((code) => [code, localeHref(code)]))
    }
  };
}

export default async function LandingPage({ params }: LandingProperties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  // Rendered per request so the API is never called during a build. `connection()` opts in to that
  // without `force-dynamic`, which would also switch off the tagged public data cache.
  await connection();

  const landing = resolveDomain(locale, "landing");
  const home = resolveDomain(locale, "home");
  const directory = resolveDomain(locale, "directory");
  const [localityRead, latestRead] = await Promise.all([
    loadLocalities(locale),
    loadProjectPage({}, locale, 50)
  ]);
  const localities = localityRead.state === "ok" ? localityRead.data : [];
  const items = latestRead.state === "ok" ? latestRead.data.items : [];
  const present = new Set(items.map((item) => item.category));
  // Only categories that actually have records are offered, in the API's own vocabulary order.
  const categories = CATEGORIES.filter((category) => present.has(category));
  const latest = items[0];
  const format = createFormatters(directory.language);

  return (
    <SiteShell locale={locale}>
      <div className="grid gap-12 lg:gap-16">
        <section
          aria-labelledby="landing-title"
          className="grid overflow-hidden border border-border bg-card lg:grid-cols-[minmax(0,1.1fr)_minmax(20rem,0.9fr)]"
          data-slot="hero"
          lang={landing.language}
        >
          <div className="grid content-center gap-5 p-6 sm:p-8 lg:p-12">
            <h1
              className="m-0 max-w-[20ch] text-[clamp(2.25rem,5vw,4.25rem)] leading-[1.02] tracking-[-0.04em] [overflow-wrap:anywhere]"
              id="landing-title"
            >
              {landing.messages.heading}
            </h1>
            <p className="m-0 max-w-[58ch] text-lg text-muted-foreground">
              {landing.messages.lead}
            </p>
            <div className="flex flex-wrap items-start gap-3">
              <ButtonLink href={`/${locale}/projects`}>
                {landing.messages.browse}
                <ArrowRight aria-hidden="true" className="size-4" />
              </ButtonLink>
              <ButtonLink href={`/${locale}/report`} variant="secondary">
                <FileWarning aria-hidden="true" className="size-4" />
                {landing.messages.report}
              </ButtonLink>
            </div>
            <p className="m-0 max-w-[52ch] text-sm text-muted-foreground">
              {landing.messages.reportNote}
            </p>
          </div>
          <div
            className="grid content-center border-t border-border bg-[var(--state-selected-background)] p-6 forced-colors:bg-[Canvas] sm:p-8 lg:border-s lg:border-t-0 lg:p-10"
            lang={home.language}
          >
            <HomeSearch
              copy={home.messages.search}
              locale={locale}
              submitLabel={home.messages.search.apply}
            />
          </div>
        </section>
        <div className="grid gap-12" lang={home.language}>
          <LatestRecord
            copy={home.messages.latest}
            directory={directory.messages}
            format={format}
            locale={locale}
            locality={localities.find((item) => item.slug === latest?.locality_slug)}
            project={latest}
            state={latestRead.state === "ok" ? "ok" : "unavailable"}
          />
          <EntryPoints
            categories={categories}
            copy={home.messages}
            directory={directory.messages}
            localities={localities}
            locale={locale}
          />
          <TrustAndSteps copy={home.messages} locale={locale} />
        </div>
      </div>
    </SiteShell>
  );
}
