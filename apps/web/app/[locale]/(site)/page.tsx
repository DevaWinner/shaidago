import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { FirstViewport } from "@/components/landing/first-viewport";
import { PublicShell } from "@/components/shell/shell";
import { translationStatusLabels } from "@/content/en/evidence";
import { landingMessages } from "@/content/en/landing";
import { publicShellMessages } from "@/content/en/shell";
import { LOCALES, REVIEWED_LOCALES, contentLocale, isSupportedLocale } from "@/i18n/routing";
import { createDateFormatter } from "@/lib/format/date";

type LandingProperties = Readonly<{ params: Promise<{ locale: string }> }>;

export default async function LandingPage({ params }: LandingProperties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const base = `/${locale}`;
  // Links to routes that later tasks build resolve to the safe not-found page meanwhile.
  const links = {
    home: base,
    localities: `${base}/localities`,
    report: `${base}/report`,
    sources: `${base}/trust#sources`,
    trust: `${base}/trust`
  } as const;
  const showsOriginal = contentLocale(locale) !== locale;

  return (
    <PublicShell
      currentLocale={locale}
      links={links}
      localeRoutes={{ en: "/en", ha: "/ha", ig: "/ig", yo: "/yo" }}
      messages={publicShellMessages}
      unreviewedLocales={LOCALES.filter((code) => !REVIEWED_LOCALES.includes(code))}
    >
      {showsOriginal ? (
        <div className="mb-6">
          <TranslationNotice labels={translationStatusLabels} status="unavailable" />
        </div>
      ) : null}
      <FirstViewport
        browseHref={`${base}/projects`}
        format={createDateFormatter(contentLocale(locale))}
        messages={landingMessages}
        reportHref={links.report}
      />
    </PublicShell>
  );
}
