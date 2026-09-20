import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { QueueFilterForm, QueueList, QueueNotice } from "@/components/reviewer/queue";
import { ReviewerFrame } from "@/components/reviewer/frame";
import { ButtonLink } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { formatMessage, resolveDomain } from "@/i18n/catalogue";
import { isSupportedLocale } from "@/i18n/routing";
import { serverApi } from "@/lib/api/server";
import { hasFilters, parseQueueFilters, queueHref, queueQuery } from "@/lib/reviewer/queue-filters";
import { queuePath } from "@/lib/reviewer/safe-return";
import { redirectToSignIn, requireSession, reviewerOptionsFor } from "@/lib/reviewer/session";

// Private, per reviewer, never cached or indexed. The address holds only triage filters and an
// opaque cursor; the list itself carries no report text, contact, or evidence.
export const dynamic = "force-dynamic";

type Properties = Readonly<{
  params: Promise<{ locale: string }>;
  searchParams: Promise<Readonly<Record<string, string | string[] | undefined>>>;
}>;

export async function generateMetadata({ params }: Pick<Properties, "params">): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: isSupportedLocale(locale)
      ? resolveDomain(locale, "reviewer").messages.queue.title
      : undefined,
    robots: { index: false, follow: false, nocache: true }
  };
}

export default async function ReviewerQueuePage({
  params,
  searchParams
}: Properties): Promise<ReactNode> {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const base = queuePath(locale);
  const options = await reviewerOptionsFor(locale);

  if (options === undefined) {
    redirectToSignIn(locale, undefined, base);
  }

  const filters = parseQueueFilters(await searchParams);
  const reviewer = resolveDomain(locale, "reviewer");
  const copy = reviewer.messages.queue;
  const result = requireSession(
    await serverApi().listReviewerReports(queueQuery(filters), options),
    locale,
    base
  );
  const firstPage = queueHref(base, filters);
  const retry = (
    <ButtonLink
      href={queueHref(
        base,
        filters,
        filters.cursor === undefined ? {} : { cursor: filters.cursor }
      )}
      variant="secondary"
    >
      {copy.states.unavailable.retry}
    </ButtonLink>
  );

  return (
    <ReviewerFrame locale={locale} signedIn>
      <h1 className="m-0 text-ledger-display leading-[1.1]">{copy.title}</h1>
      <p className="m-0 max-w-[68ch]">{copy.lead}</p>
      <QueueFilterForm action={base} clearHref={base} copy={copy} filters={filters} />
      <section aria-labelledby="queue-results" className="grid gap-4" id="results">
        <h2 className="m-0 text-ledger-lg" id="queue-results">
          {copy.results.heading}
        </h2>
        {result.kind === "ok" ? (
          result.data.items.length === 0 ? (
            hasFilters(filters) ? (
              <QueueNotice
                action={
                  <div>
                    <ButtonLink href={base} variant="secondary">
                      {copy.filters.clear}
                    </ButtonLink>
                  </div>
                }
                body={copy.states.noMatches.body}
                title={copy.states.noMatches.title}
              />
            ) : (
              <QueueNotice body={copy.states.empty.body} title={copy.states.empty.title} />
            )
          ) : (
            <>
              <p className="m-0" role="status">
                {formatMessage(reviewer.language, copy.results.count, {
                  count: result.data.items.length
                })}
              </p>
              <QueueList
                copy={copy}
                items={result.data.items}
                language={reviewer.language}
                locale={locale}
              />
              <Pagination
                label={copy.results.paginationLabel}
                {...(result.data.next_cursor === null
                  ? {}
                  : {
                      next: {
                        href: `${queueHref(base, filters, { cursor: result.data.next_cursor })}#results`,
                        label: copy.results.next
                      }
                    })}
                {...(filters.cursor === undefined
                  ? {}
                  : { previous: { href: `${firstPage}#results`, label: copy.results.first } })}
              />
            </>
          )
        ) : result.kind === "problem" && result.problem.code === "invalid_cursor" ? (
          <QueueNotice
            action={
              <div>
                <ButtonLink href={firstPage} variant="secondary">
                  {copy.results.first}
                </ButtonLink>
              </div>
            }
            body={copy.states.invalidCursor.body}
            title={copy.states.invalidCursor.title}
          />
        ) : result.kind === "problem" && result.problem.status === 403 ? (
          <QueueNotice body={copy.states.forbidden.body} title={copy.states.forbidden.title} />
        ) : result.kind === "problem" && result.problem.status === 429 ? (
          <QueueNotice body={copy.states.rateLimited.body} title={copy.states.rateLimited.title} />
        ) : (
          <QueueNotice
            action={<div>{retry}</div>}
            body={copy.states.unavailable.body}
            title={copy.states.unavailable.title}
          />
        )}
      </section>
    </ReviewerFrame>
  );
}
