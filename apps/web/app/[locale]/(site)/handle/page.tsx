import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";
import { KeyRound } from "lucide-react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { SiteShell } from "@/components/shell/site-shell";
import { PageHeader } from "@/components/ui/page-header";
import { HandlePanel } from "@/components/track/handle-panel";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";

// Per visitor and never cached or indexed: a created handle and passphrase exist only in the page's
// memory while it is open.
export const dynamic = "force-dynamic";

type Properties = Readonly<{ params: Promise<{ locale: string }> }>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale) ? resolveDomain(locale, "handle").messages.title : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

export default async function HandlePage({ params }: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const handle = resolveDomain(locale, "handle");
  const evidence = resolveDomain(locale, "evidence");
  const problems = resolveDomain(locale, "problems");

  return (
    <SiteShell locale={locale} route={{ segments: ["handle"] }}>
      <div className="grid gap-6" lang={handle.language}>
        {handle.isOriginal || problems.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <PageHeader
          icon={KeyRound}
          intro={<p>{handle.messages.lead}</p>}
          title={handle.messages.title}
        />
        <HandlePanel
          copy={handle.messages}
          locale={locale}
          problems={problems.messages}
          trackHref={`/${locale}/track`}
        />
      </div>
    </SiteShell>
  );
}
