import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { SiteShell } from "@/components/shell/site-shell";
import { TrackPanel } from "@/components/track/track-panel";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";

// Per visitor and never cached or indexed. Nothing about a report is read from the address: the
// tracking code and handle credentials are sent only in a POST body when the person presses a button.
export const dynamic = "force-dynamic";

type Properties = Readonly<{ params: Promise<{ locale: string }> }>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale) ? resolveDomain(locale, "track").messages.title : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

export default async function TrackPage({ params }: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const track = resolveDomain(locale, "track");
  const evidence = resolveDomain(locale, "evidence");
  const problems = resolveDomain(locale, "problems");

  return (
    <SiteShell locale={locale} route={{ segments: ["track"] }}>
      <div className="grid gap-6" lang={track.language}>
        {track.isOriginal || problems.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <h1 className="m-0 text-ledger-display leading-[1.1]">{track.messages.title}</h1>
        <p className="m-0 max-w-[68ch]">{track.messages.lead}</p>
        <TrackPanel
          copy={track.messages}
          language={track.language}
          locale={locale}
          problems={problems.messages}
          reportHref={`/${locale}/report`}
        />
      </div>
    </SiteShell>
  );
}
