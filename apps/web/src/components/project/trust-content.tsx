import type { ReactNode } from "react";
import { ShieldCheck } from "lucide-react";

import { InformationClassMarker, VerificationLabel } from "@/components/evidence/evidence";
import { ButtonLink } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import type { Messages } from "@/i18n/catalogue";

const section = "grid gap-3 border-t border-border pt-8";
const heading = "m-0 text-ledger-xl leading-tight";

const CLASS_ORDER = [
  "official_source",
  "independent_source",
  "community_evidence_reviewed",
  "community_report_unverified",
  "ai_generated_explanation"
] as const;
const STATE_ORDER = [
  "awaiting_verification",
  "verified_official",
  "corroborated",
  "community_reviewed",
  "disputed",
  "outdated"
] as const;

/**
 * The trust page. Its examples are the real labels the record pages use (the same components and
 * words), so what is explained here is what a resident sees there. It makes no legal or protection
 * promise and points to one correction route: a private report.
 */
export function TrustContent({
  copy,
  directoryHref,
  evidence,
  locale
}: Readonly<{
  copy: Messages["trust"];
  directoryHref: string;
  evidence: Messages["evidence"];
  locale: string;
}>): ReactNode {
  const toc = [
    ["classes", copy.classes.heading],
    ["states", copy.states.heading],
    ["citations", copy.citations.heading],
    ["ai", copy.ai.heading],
    ["scout", copy.scout.heading],
    ["review", copy.review.heading],
    ["reporting", copy.reporting.heading],
    ["correct", copy.correct.heading]
  ] as const;

  return (
    <div className="grid max-w-[76ch] gap-8">
      <PageHeader icon={ShieldCheck} intro={<p>{copy.lead}</p>} title={copy.title} />

      <nav aria-label={copy.toc} className="grid gap-1">
        <ul className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1 p-0">
          {toc.map(([id, label]) => (
            <li key={id}>
              <a
                className="inline-flex min-h-11 items-center font-semibold text-ledger-accent-strong"
                href={`#${id}`}
              >
                {label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <section aria-labelledby="classes" className={section}>
        <h2 className={heading} id="classes">
          {copy.classes.heading}
        </h2>
        <p className="m-0">{copy.classes.intro}</p>
        <dl className="m-0 grid gap-4">
          {CLASS_ORDER.map((value) => (
            <div className="grid gap-1" key={value}>
              <dt>
                <InformationClassMarker labels={evidence.informationClass} value={value} />
              </dt>
              <dd className="m-0">{copy.classes[value]}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="states" className={section}>
        <h2 className={heading} id="states">
          {copy.states.heading}
        </h2>
        <p className="m-0">{copy.states.intro}</p>
        <dl className="m-0 grid gap-4">
          {STATE_ORDER.map((value) => (
            <div className="grid gap-1" key={value}>
              <dt>
                <VerificationLabel labels={evidence.verification} state={value} />
              </dt>
              <dd className="m-0">{copy.states[value]}</dd>
            </div>
          ))}
        </dl>
      </section>

      {(
        [
          ["citations", copy.citations],
          ["ai", copy.ai],
          ["scout", copy.scout],
          ["review", copy.review]
        ] as const
      ).map(([id, block]) => (
        <section
          aria-labelledby={id}
          className={section}
          id={id === "citations" ? "sources" : undefined}
          key={id}
        >
          <h2 className={heading} id={id}>
            {block.heading}
          </h2>
          <p className="m-0">{block.body}</p>
        </section>
      ))}

      <section aria-labelledby="reporting" className={section}>
        <h2 className={heading} id="reporting">
          {copy.reporting.heading}
        </h2>
        <p className="m-0">{copy.reporting.body}</p>
        <p className="m-0 font-semibold">{copy.reporting.limit}</p>
      </section>

      <section aria-labelledby="correct" className={section}>
        <h2 className={heading} id="correct">
          {copy.correct.heading}
        </h2>
        <p className="m-0">{copy.correct.body}</p>
        <div>
          <ButtonLink href={`/${locale}/report`} variant="secondary">
            {copy.correct.report}
          </ButtonLink>
        </div>
      </section>

      <p className="m-0">
        <a className="font-semibold text-ledger-accent-strong underline" href={directoryHref}>
          {copy.back}
        </a>
      </p>
    </div>
  );
}
