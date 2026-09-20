import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { Confirmation } from "@/components/report/confirmation";
import { SiteShell } from "@/components/shell/site-shell";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";

// The receipt lives only in the browser's memory. This page holds no code, is never cached or
// indexed, and reads nothing from the address, so a direct visit shows the honest "gone" state.
export const dynamic = "force-dynamic";

type Properties = Readonly<{ params: Promise<{ locale: string }> }>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale)
      ? resolveDomain(locale, "report").messages.complete.title
      : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

export default async function ReportCompletePage({ params }: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const report = resolveDomain(locale, "report");
  const evidence = resolveDomain(locale, "evidence");

  return (
    <SiteShell locale={locale} route={{ segments: ["report", "complete"] }}>
      <div className="grid gap-6" lang={report.language}>
        {report.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <Confirmation copy={report.messages} locale={locale} />
      </div>
    </SiteShell>
  );
}
