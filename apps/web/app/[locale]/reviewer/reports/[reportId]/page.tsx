import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { QueueNotice } from "@/components/reviewer/queue";
import { ReviewerFrame } from "@/components/reviewer/frame";
import { AskQuestionForm, WithdrawQuestionButton } from "@/components/reviewer/question-controls";
import { EvidenceDownload } from "@/components/reviewer/evidence-download";
import { PublicUpdatePanel } from "@/components/reviewer/public-update-panel";
import { StatusActions } from "@/components/reviewer/status-actions";
import { NoteForm } from "@/components/reviewer/note-form";
import {
  ContactSection,
  DemoWarning,
  EvidenceSection,
  HandleSection,
  HistorySection,
  NotesSection,
  ObservationSection,
  QuestionsList,
  ReportHeader,
  ScoutSection,
  Section,
  detailContext,
  type ContactOutcome,
  type NotesView
} from "@/components/reviewer/report-detail";
import { ButtonLink, Link } from "@/components/ui/button";
import { resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";
import { idParam } from "@/lib/bff/reviewer-schemas";
import { loadProject } from "@/lib/api/public-data";
import { serverApi } from "@/lib/api/server";
import { citationOptions } from "@/lib/reviewer/publication";
import { queuePath, signInPath } from "@/lib/reviewer/safe-return";
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
  const rawNotes = query["notes"];
  const notesCursor =
    typeof rawNotes === "string" && /^[\x21-\x7e]{1,512}$/.test(rawNotes) ? rawNotes : undefined;
  const notesResult = requireSession(
    await api.listReviewerNotes(
      reportId,
      { limit: 20, ...(notesCursor === undefined ? {} : { cursor: notesCursor }) },
      options
    ),
    locale,
    self
  );
  const notes: NotesView =
    notesResult.kind === "ok"
      ? {
          state: "ok",
          items: notesResult.data.items,
          nextHref:
            notesResult.data.next_cursor === null
              ? undefined
              : `${self}?notes=${encodeURIComponent(notesResult.data.next_cursor)}#notes`,
          firstHref: notesCursor === undefined ? undefined : `${self}#notes`
        }
      : { state: "unavailable", retryHref: `${self}#notes` };
  const [draftsResult, projectResult] = await Promise.all([
    api.listPublicationDrafts(reportId, options),
    loadProject(report.project_slug, reviewer.language)
  ]);
  const drafts = requireSession(draftsResult, locale, self);
  const signInHref = signInPath(locale, { reason: "expired", next: self });
  const entryCopy = {
    directory: resolveDomain(locale, "directory").messages,
    evidence: resolveDomain(locale, "evidence").messages,
    project: resolveDomain(locale, "project").messages,
    source: resolveDomain(locale, "source").messages
  };
  const shared = {
    actions: reviewer.messages.actions,
    locale,
    problems: resolveDomain(locale, "problems").messages,
    reportId,
    signInHref
  };
  const context = detailContext(copy, reviewer.messages.queue, reviewer.language, locale);
  const anchors = [
    "status",
    "observation",
    "evidence",
    "contact",
    "history",
    "questions",
    "notes",
    "handle",
    "scout",
    "publication"
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
        <StatusActions
          {...shared}
          copy={reviewer.messages.transition}
          status={report.status}
          statuses={reviewer.messages.queue.statuses}
          version={report.version}
        />
      </Section>
      <DemoWarning copy={copy} />
      <ObservationSection context={context} report={report} />
      <EvidenceSection
        context={context}
        renderDownload={(file) => (
          <EvidenceDownload
            actions={shared.actions}
            copy={reviewer.messages.download}
            evidenceId={file.evidence_id}
            fileName={file.display_name}
            problems={shared.problems}
            reportId={reportId}
            signInHref={signInHref}
          />
        )}
        report={report}
      />
      <ContactSection
        context={context}
        hideHref={self}
        outcome={outcome}
        report={report}
        revealHref={self}
      />
      <HistorySection context={context} report={report} />
      <Section id="questions" title={copy.sections.questions}>
        <QuestionsList
          context={context}
          renderActions={(item) => (
            <WithdrawQuestionButton
              {...shared}
              copy={reviewer.messages.questionActions}
              question={item.question}
              questionId={item.question_id}
            />
          )}
          report={report}
        />
        <AskQuestionForm {...shared} copy={reviewer.messages.questionActions} />
      </Section>
      <NotesSection
        context={context}
        form={<NoteForm {...shared} copy={reviewer.messages.notes} />}
        notes={notes}
        words={reviewer.messages.notes}
      />
      <HandleSection context={context} report={report} />
      <ScoutSection context={context} />
      <Section id="publication" title={copy.sections.publication}>
        <PublicUpdatePanel
          actions={shared.actions}
          copy={reviewer.messages.publication}
          drafts={
            drafts.kind === "ok"
              ? drafts.data.items.map((item) => ({
                  id: item.public_update_id,
                  state: item.state,
                  createdAt: item.created_at
                }))
              : []
          }
          entryCopy={entryCopy}
          language={reviewer.language}
          locale={locale}
          now={new Date().toISOString()}
          options={projectResult.state === "ok" ? citationOptions(projectResult.data) : undefined}
          problems={shared.problems}
          projectHref={`/${locale}/projects/${encodeURIComponent(report.project_slug)}`}
          reportId={reportId}
          reportVerified={report.status === "verified_for_public_update"}
          signInHref={signInHref}
        />
      </Section>
    </ReviewerFrame>
  );
}
