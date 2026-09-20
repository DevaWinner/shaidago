import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { setRequestLocale } from "next-intl/server";
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
      <div className="grid gap-10">
        <section
          aria-labelledby="landing-title"
          className="grid gap-4"
          data-slot="hero"
          lang={landing.language}
        >
          <p className="m-0 text-sm font-bold tracking-wide text-muted-foreground uppercase">
            {landing.messages.recordKind}
          </p>
          <h1
            className="m-0 max-w-[24ch] text-[clamp(1.75rem,3.4vw,2.75rem)] leading-[1.1] [overflow-wrap:anywhere]"
            id="landing-title"
          >
            {landing.messages.heading}
          </h1>
          <p className="m-0 max-w-[60ch]">{landing.messages.lead}</p>
          <div lang={home.language}>
            <HomeSearch
              copy={home.messages.search}
              locale={locale}
              submitLabel={home.messages.search.apply}
            />
          </div>
          <div className="flex flex-wrap items-start gap-4">
            <ButtonLink href={`/${locale}/projects`} lang={landing.language} variant="secondary">
              {landing.messages.browse}
            </ButtonLink>
            <div className="grid max-w-[30ch] gap-1" lang={landing.language}>
              <ButtonLink href={`/${locale}/report`} variant="secondary">
                {landing.messages.report}
              </ButtonLink>
              <p className="m-0 text-sm text-muted-foreground">{landing.messages.reportNote}</p>
            </div>
          </div>
        </section>
        <div className="grid gap-10" lang={home.language}>
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
