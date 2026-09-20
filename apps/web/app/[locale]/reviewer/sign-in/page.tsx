import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { Callout } from "@/components/ui/feedback";
import { ReviewerFrame } from "@/components/reviewer/frame";
import { SignInForm } from "@/components/reviewer/sign-in-form";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";
import { queuePath, safeReviewerTarget, toSignInReason } from "@/lib/reviewer/safe-return";

// Per visitor, never cached, never indexed. The return target is rebuilt from an allowlist, so the
// address can never redirect a reviewer anywhere but their own queue or one report.
export const dynamic = "force-dynamic";

type Properties = Readonly<{
  params: Promise<{ locale: string }>;
  searchParams: Promise<Readonly<Record<string, string | string[] | undefined>>>;
}>;

export async function generateMetadata({ params }: Pick<Properties, "params">): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale)
      ? resolveDomain(locale, "reviewer").messages.signIn.title
      : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

export default async function ReviewerSignInPage({
  params,
  searchParams
}: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const query = await searchParams;
  const copy = resolveDomain(locale, "reviewer").messages;
  const problems = resolveDomain(locale, "problems").messages;
  const reason = toSignInReason(typeof query["reason"] === "string" ? query["reason"] : undefined);
  const target = safeReviewerTarget(locale, query["next"]) ?? queuePath(locale);

  return (
    <ReviewerFrame locale={locale} signedIn={false}>
      <h1 className="m-0 text-ledger-display leading-[1.1]">{copy.signIn.title}</h1>
      <p className="m-0 max-w-[68ch]">{copy.signIn.lead}</p>
      {reason === undefined ? null : (
        <Callout title={copy.signIn.reasons[reason]} tone="information">
          {copy.signIn.note}
        </Callout>
      )}
      <noscript>
        <p>{copy.signIn.needsScript}</p>
      </noscript>
      <SignInForm
        copy={copy.signIn}
        problems={problems}
        required={copy.signIn.required}
        target={target}
      />
    </ReviewerFrame>
  );
}
