import type { ReactNode } from "react";

import {
  AiExplanationNotice,
  EvidenceGap,
  TranslationNotice
} from "@/components/evidence/evidence";
import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import type { Formatters } from "@/lib/format/formatters";
import type { AnswerOutcome, AnswerSource, AnswerView } from "@/lib/qa/answer";

const LONG = 420;

function Passage({ copy, source }: Readonly<{ copy: Messages["qa"]; source: AnswerSource }>) {
  const full = source.passage;
  const quote = "m-0 max-w-[68ch] font-ledger-documentary leading-[1.7] [overflow-wrap:anywhere]";

  if (full.length <= LONG) {
    return <blockquote className={quote}>{full}</blockquote>;
  }

  return (
    <>
      <blockquote className={quote}>{`${full.slice(0, LONG).trimEnd()}…`}</blockquote>
      <details className="max-w-[68ch]">
        <summary className="min-h-11 cursor-pointer py-2 font-semibold">
          {copy.result.showFull}
        </summary>
        <blockquote className={quote}>{full}</blockquote>
      </details>
    </>
  );
}

function SupportedAnswer({
  base,
  copy,
  evidence,
  format,
  view
}: Readonly<{
  base: string;
  copy: Messages["qa"];
  evidence: Messages["evidence"];
  format: Formatters;
  view: AnswerView;
}>): ReactNode {
  const text = copy.result;
  const firstUse = (number: number): number =>
    Math.max(
      view.statements.findIndex((statement) => statement.sources.includes(number)),
      0
    );

  return (
    <div className="grid gap-5">
      <AiExplanationNotice label={text.aiLabel}>
        <ul className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1 p-0 text-sm text-muted-foreground">
          <li>{formatMessageLite(text.generated, { time: format.dateTime(view.generatedAt) })}</li>
          <li>{view.mode === "hybrid" ? text.retrievalHybrid : text.retrievalKeyword}</li>
          <li>{formatMessageLite(text.considered, { count: view.chunksConsidered })}</li>
        </ul>
        {view.mode === "keyword" ? <p className="m-0 mt-2 text-sm">{text.keywordCaution}</p> : null}
      </AiExplanationNotice>
      {view.servedLocale === view.requestedLocale ? null : (
        <TranslationNotice labels={evidence.translation} status="unavailable" />
      )}
      <section aria-labelledby="qa-statements-heading" className="grid gap-3">
        <h4 className="m-0 text-ledger-lg" id="qa-statements-heading">
          {text.statementsHeading}
        </h4>
        <ol className="m-0 grid list-none gap-4 p-0" lang={view.servedLocale}>
          {view.statements.map((statement, index) => (
            <li
              className="grid gap-2 border border-border border-s-[0.375rem] border-s-border bg-card p-4 target:border-s-ledger-accent-strong"
              id={`qa-statement-${index + 1}`}
              key={`${index}-${statement.text}`}
            >
              <p className="m-0 max-w-[68ch] [overflow-wrap:anywhere]">{statement.text}</p>
              <p className="m-0 flex flex-wrap items-center gap-x-3 text-sm">
                <span className="text-muted-foreground">{text.cites}</span>
                {statement.sources.map((number) => (
                  <a
                    className="inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong underline"
                    href={`#qa-source-${number}`}
                    key={number}
                  >
                    {formatMessageLite(text.sourceLabel, { number })}
                  </a>
                ))}
              </p>
            </li>
          ))}
        </ol>
        {view.confidenceNote === "" ? null : (
          <p className="m-0 max-w-[68ch] text-sm text-muted-foreground" lang={view.servedLocale}>
            <strong>{text.noteLabel}:</strong> {view.confidenceNote}
          </p>
        )}
      </section>
      <section aria-labelledby="qa-sources-heading" className="grid gap-3">
        <h4 className="m-0 text-ledger-lg" id="qa-sources-heading">
          {text.sourcesHeading}
        </h4>
        <ol className="m-0 grid list-none gap-4 p-0">
          {view.sources.map((source) => (
            <li
              className="grid gap-2 border border-border border-s-[0.375rem] border-s-border bg-card p-4 target:border-s-ledger-accent-strong"
              id={`qa-source-${source.number}`}
              key={source.citationId}
            >
              <p className="m-0 font-semibold [overflow-wrap:anywhere]">
                {formatMessageLite(text.sourceLabel, { number: source.number })}: {source.title}
              </p>
              <p className="m-0 text-sm text-muted-foreground [overflow-wrap:anywhere]">
                {source.publisher}
                {source.sectionLabel === null ? "" : ` · ${text.location}: ${source.sectionLabel}`}
                {" · "}
                {formatMessageLite(text.retrieved, { date: format.date(source.retrievedAt) })}
              </p>
              <Passage copy={copy} source={source} />
              <p className="m-0 flex flex-wrap gap-x-5 text-sm">
                <a
                  className="inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong underline"
                  href={`${base}/sources/${source.sourceId}`}
                >
                  {text.openSourcePage}
                </a>
                <a
                  className="inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong underline"
                  href={source.url}
                  referrerPolicy="no-referrer"
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {text.openOriginal}
                  <span className="sr-only"> ({text.newTab})</span>
                </a>
                <a
                  className="inline-flex min-h-11 items-center text-ledger-accent-strong underline"
                  href={`#qa-statement-${firstUse(source.number) + 1}`}
                >
                  {text.backToStatement}
                </a>
              </p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

/**
 * What a finished question shows. A supported answer is its statements, each linked to the sources
 * it cites within this response. Insufficient evidence and a rejected answer never render any
 * generated statement, and never replace the refusal with prose of our own.
 */
export function QuestionAnswer({
  base,
  copy,
  evidence,
  factsHref,
  format,
  outcome
}: Readonly<{
  base: string;
  copy: Messages["qa"];
  evidence: Messages["evidence"];
  factsHref: string;
  format: Formatters;
  outcome: Exclude<AnswerOutcome, { kind: "invalid" }>;
}>): ReactNode {
  if (outcome.kind === "insufficient") {
    return (
      <EvidenceGap kind="insufficient_evidence" title={copy.insufficient.title}>
        <div className="grid gap-2">
          <p className="m-0">{copy.insufficient.body}</p>
          {outcome.answer === "" ? null : (
            <p className="m-0" lang={outcome.servedLocale}>
              {outcome.answer}
            </p>
          )}
          {outcome.confidenceNote === "" ? null : (
            <p className="m-0 text-sm text-muted-foreground" lang={outcome.servedLocale}>
              {outcome.confidenceNote}
            </p>
          )}
          <a
            className="inline-flex min-h-11 w-fit items-center font-semibold text-ledger-accent-strong underline"
            href={factsHref}
          >
            {copy.insufficient.read}
          </a>
        </div>
      </EvidenceGap>
    );
  }

  if (outcome.kind === "rejected") {
    return (
      <EvidenceGap kind="information_gap" title={copy.rejected.title}>
        <p className="m-0">{copy.rejected.body}</p>
      </EvidenceGap>
    );
  }

  return (
    <SupportedAnswer
      base={base}
      copy={copy}
      evidence={evidence}
      format={format}
      view={outcome.view}
    />
  );
}
