import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";
import { WifiOff } from "lucide-react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { RetryButton } from "@/components/pwa/retry-button";
import { SavedPages } from "@/components/pwa/saved-pages";
import { SiteShell } from "@/components/shell/site-shell";
import { PageHeader } from "@/components/ui/page-header";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";

// Static and free of any API call, so the service worker can precache it for every language.
type Properties = Readonly<{ params: Promise<{ locale: string }> }>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale) ? resolveDomain(locale, "offline").messages.title : undefined,
    robots: { index: false, follow: false }
  };
}

export default async function OfflinePage({ params }: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) notFound();

  setRequestLocale(locale);
  const copy = resolveDomain(locale, "offline");
  const evidence = resolveDomain(locale, "evidence");

  return (
    <SiteShell locale={locale} route={{ segments: ["offline"] }}>
      <div className="grid gap-6" lang={copy.language}>
        {copy.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <PageHeader
          icon={WifiOff}
          intro={<p>{copy.messages.lead}</p>}
          title={copy.messages.title}
        />
        <div>
          <RetryButton label={copy.messages.retry} />
        </div>
        <SavedPages copy={copy.messages} language={copy.language} />
        <p className="m-0 max-w-[68ch] text-sm">{copy.messages.privateNote}</p>
      </div>
    </SiteShell>
  );
}
