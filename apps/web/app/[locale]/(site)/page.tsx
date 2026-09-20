import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { FirstViewport } from "@/components/landing/first-viewport";
import { PublicShell } from "@/components/shell/shell";
import { formatMessage, resolveDomain } from "@/i18n/catalogue";
import { LOCALES, REVIEWED_LOCALES, isSupportedLocale } from "@/i18n/routing";
import { createFormatters } from "@/lib/format/formatters";

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
  const shell = resolveDomain(locale, "shell");
  const evidence = resolveDomain(locale, "evidence");
  const landing = resolveDomain(locale, "landing");
  // Any critical domain served as the English original must be announced, never silent.
  const showsOriginal = shell.isOriginal || evidence.isOriginal || landing.isOriginal;
  const sample = landing.messages.sample;

  return (
    <PublicShell
      currentLocale={locale}
      links={links}
      localeRoutes={{ en: "/en", ha: "/ha", ig: "/ig", yo: "/yo" }}
      messages={shell.messages.public}
      unreviewedLocales={LOCALES.filter((code) => !REVIEWED_LOCALES.includes(code))}
    >
      {showsOriginal ? (
        <div className="mb-6">
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        </div>
      ) : null}
      <FirstViewport
        browseHref={`${base}/projects`}
        evidence={evidence.messages}
        format={createFormatters(landing.language).date}
        messages={landing.messages}
        reportHref={links.report}
        sourceCountText={formatMessage(landing.language, sample.sourceCount, { count: 1 })}
        sourceLabelText={formatMessage(landing.language, sample.sourceLabel, { number: 1 })}
      />
    </PublicShell>
  );
}
