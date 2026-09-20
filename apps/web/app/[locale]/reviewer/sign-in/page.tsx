import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";
import { LockKeyhole } from "lucide-react";

import { Callout } from "@/components/ui/feedback";
import { PageHeader } from "@/components/ui/page-header";
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
      <PageHeader icon={LockKeyhole} intro={<p>{copy.signIn.lead}</p>} title={copy.signIn.title} />
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
