import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { TrustContent } from "@/components/project/trust-content";
import { SiteShell } from "@/components/shell/site-shell";
import { resolveDomain } from "@/i18n/catalogue";
import { LOCALES, isSupportedLocale } from "@/i18n/routing";

type Properties = Readonly<{ params: Promise<{ locale: string }> }>;

export async function generateMetadata({ params }: Properties): Promise<Metadata> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    return {};
  }

  const copy = resolveDomain(locale, "trust").messages;

  return {
    title: copy.title,
    description: copy.lead,
    alternates: {
      canonical: `/${locale}/trust`,
      languages: Object.fromEntries(LOCALES.map((code) => [code, `/${code}/trust`]))
    }
  };
}

export default async function TrustPage({ params }: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const trust = resolveDomain(locale, "trust");
  const evidence = resolveDomain(locale, "evidence");

  return (
    <SiteShell locale={locale} route={{ segments: ["trust"] }}>
      <div className="grid gap-6" lang={trust.language}>
        {trust.isOriginal || evidence.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <TrustContent
          copy={trust.messages}
          directoryHref={`/${locale}/projects`}
          evidence={evidence.messages}
          locale={locale}
        />
      </div>
    </SiteShell>
  );
}
