import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { QueueNotice } from "@/components/reviewer/queue";
import { ReviewerFrame } from "@/components/reviewer/frame";
import {
  ContactSection,
  DemoWarning,
  EvidenceSection,
  HandleSection,
  HistorySection,
  ObservationSection,
  QuestionsList,
  ReportHeader,
  ScoutSection,
  Section,
  detailContext,
  type ContactOutcome
} from "@/components/reviewer/report-detail";
import { ButtonLink, Link } from "@/components/ui/button";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";
import { idParam } from "@/lib/bff/reviewer-schemas";
import { serverApi } from "@/lib/api/server";
import { queuePath } from "@/lib/reviewer/safe-return";
import { redirectToSignIn, requireSession, reviewerOptionsFor } from "@/lib/reviewer/session";

// Private, per reviewer, never cached, prefetched, or indexed. The address holds the opaque report
// ID and, at most, the word `reveal=contact`: the contact value itself is never in it.
export const dynamic = "force-dynamic";

type Properties = Readonly<{
  params: Promise<{ locale: string; reportId: string }>;
  searchParams: Promise<Readonly<Record<string, string | string[] | undefined>>>;
}>;

export async function generateMetadata({ params }: Pick<Properties, "params">): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale)
      ? resolveDomain(locale, "reviewer").messages.detail.title
      : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

export default async function ReviewerReportPage({
  params,
  searchParams
}: Properties): Promise<ReactNode> {
  const { locale, reportId: rawId } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const reviewer = resolveDomain(locale, "reviewer");
  const copy = reviewer.messages.detail;
  const parsed = idParam.safeParse(rawId);
  const queue = queuePath(locale);
  const missing = (
    <ReviewerFrame locale={locale} signedIn>
      <QueueNotice
        action={
          <div>
            <ButtonLink href={queue} variant="secondary">
              {copy.back}
            </ButtonLink>
          </div>
        }
        body={copy.states.notFound.body}
        title={copy.states.notFound.title}
      />
    </ReviewerFrame>
  );

  // A malformed identifier never reaches the API and looks exactly like an unknown one.
  if (!parsed.success) {
    return missing;
  }

  const reportId = parsed.data;
  const self = `${queue}/${reportId}`;
  const options = await reviewerOptionsFor(locale);

  if (options === undefined) {
    redirectToSignIn(locale, undefined, self);
  }

  const query = await searchParams;
  const wantsContact = query["reveal"] === "contact";
  const api = serverApi();
  let outcome: ContactOutcome = "not_requested";
  let result = requireSession(
    await api.getReviewerReport(reportId, wantsContact, options),
    locale,
    self
  );

  if (wantsContact) {
    if (result.kind === "ok") {
      outcome = "shown";
    } else {
      // Contact needs its own capability. Fall back to the report without it so the reviewer can
      // still work, and say plainly why the contact is not shown.
      outcome =
        result.kind === "problem" && result.problem.status === 403 ? "denied" : "unavailable";
      result = requireSession(await api.getReviewerReport(reportId, false, options), locale, self);
    }
  }

  if (result.kind !== "ok") {
    const state =
      result.kind === "problem" && result.problem.status === 404
        ? copy.states.notFound
        : result.kind === "problem" && result.problem.status === 403
          ? copy.states.forbidden
          : result.kind === "problem" && result.problem.status === 429
            ? copy.states.rateLimited
            : copy.states.unavailable;
    const retryable = state === copy.states.unavailable;

    return (
      <ReviewerFrame locale={locale} signedIn>
        <QueueNotice
          action={
            <div className="flex flex-wrap gap-3">
              {retryable ? (
                <ButtonLink href={self} variant="secondary">
                  {copy.states.unavailable.retry}
                </ButtonLink>
              ) : null}
              <ButtonLink href={queue} variant="secondary">
                {copy.back}
              </ButtonLink>
            </div>
          }
          body={state.body}
          title={state.title}
        />
      </ReviewerFrame>
    );
  }

  const report = result.data;
  const context = detailContext(copy, reviewer.messages.queue, reviewer.language, locale);
  const anchors = [
    "status",
    "observation",
    "evidence",
    "contact",
    "history",
    "questions",
    "handle",
    "scout"
  ] as const;

  return (
    <ReviewerFrame locale={locale} signedIn>
      <p className="m-0">
        <Link href={queue}>{copy.back}</Link>
      </p>
      <h1 className="m-0 text-ledger-display leading-[1.1]">{copy.title}</h1>
      <nav aria-label={copy.jump}>
        <ul className="m-0 flex list-none flex-wrap gap-x-4 gap-y-1 p-0 text-sm">
          {anchors.map((anchor) => (
            <li key={anchor}>
              <Link href={`#${anchor}`}>{copy.sections[anchor]}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <Section id="status" title={copy.sections.status}>
        <ReportHeader context={context} report={report} />
      </Section>
      <DemoWarning copy={copy} />
      <ObservationSection context={context} report={report} />
      <EvidenceSection context={context} renderDownload={() => null} report={report} />
      <ContactSection
        context={context}
        hideHref={self}
        outcome={outcome}
        report={report}
        revealHref={self}
      />
      <HistorySection context={context} report={report} />
      <Section id="questions" title={copy.sections.questions}>
        <QuestionsList context={context} report={report} />
      </Section>
      <HandleSection context={context} report={report} />
      <ScoutSection context={context} />
    </ReviewerFrame>
  );
}
