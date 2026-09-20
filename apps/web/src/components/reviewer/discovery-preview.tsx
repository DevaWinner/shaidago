"use client";

import { useId, useState, type ReactNode } from "react";

import { ActionFeedback } from "@/components/reviewer/action-feedback";
import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/field";
import { ConfirmDialog } from "@/components/ui/overlay";
import type { Messages } from "@/i18n/catalogue";
import { networkProblem } from "@/lib/problems/browser-problem";
import type { SafeProblem } from "@/lib/problems/problem-messages";
import { postJson } from "@/lib/tracking/client";

type Copy = Messages["reviewer"]["detail"]["scout"];
type Plan = Readonly<{
  digest: string;
  policyVersion: string;
  query: string;
  terms: readonly Readonly<{ source: string; text: string }>[];
  rejected: readonly Readonly<{ reason: string; source: string }>[];
}>;

const DIGEST = /^[0-9a-f]{64}$/;
const TEXT = /^[^\u0000]{1,240}$/;

function record(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Only the bounded, public-safe plan shape reaches this island. Unknown fields remain inert. */
function parsePlan(value: unknown): Plan | undefined {
  if (
    !record(value) ||
    typeof value["plan_digest"] !== "string" ||
    !DIGEST.test(value["plan_digest"]) ||
    typeof value["policy_version"] !== "string" ||
    !TEXT.test(value["policy_version"]) ||
    typeof value["query"] !== "string" ||
    !TEXT.test(value["query"]) ||
    !Array.isArray(value["terms"]) ||
    !Array.isArray(value["rejected"]) ||
    value["terms"].length > 20 ||
    value["rejected"].length > 20
  ) {
    return undefined;
  }

  const terms: { source: string; text: string }[] = [];
  const rejected: { reason: string; source: string }[] = [];

  for (const item of value["terms"]) {
    if (
      !record(item) ||
      typeof item["source"] !== "string" ||
      typeof item["text"] !== "string" ||
      !TEXT.test(item["source"]) ||
      !TEXT.test(item["text"])
    )
      return undefined;
    terms.push({ source: item["source"], text: item["text"] });
  }
  for (const item of value["rejected"]) {
    if (
      !record(item) ||
      typeof item["reason"] !== "string" ||
      typeof item["source"] !== "string" ||
      !TEXT.test(item["reason"]) ||
      !TEXT.test(item["source"])
    )
      return undefined;
    rejected.push({ reason: item["reason"], source: item["source"] });
  }
  return {
    digest: value["plan_digest"],
    policyVersion: value["policy_version"],
    query: value["query"],
    terms,
    rejected
  };
}

function conceptsFrom(value: string): readonly string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 20);
}

/**
 * A reviewer sees and explicitly approves the exact external query. This island never receives the
 * report description, contacts, evidence, or tracking credentials; the API re-checks every term.
 */
export function DiscoveryPreview({
  actions,
  copy,
  locale,
  problems,
  reportId,
  signInHref
}: Readonly<{
  actions: Messages["reviewer"]["actions"];
  copy: Copy;
  locale: string;
  problems: Messages["problems"];
  reportId: string;
  signInHref: string;
}>): ReactNode {
  const id = useId();
  const base = `/api/reviewer/reports/${encodeURIComponent(reportId)}/discovery`;
  const [conceptsText, setConceptsText] = useState("");
  const [plan, setPlan] = useState<Plan | undefined>();
  const [busy, setBusy] = useState<"plan" | "start" | undefined>();
  const [problem, setProblem] = useState<SafeProblem>();
  const [success, setSuccess] = useState<string>();
  const [confirmOpen, setConfirmOpen] = useState(false);

  async function prepare(): Promise<void> {
    if (busy !== undefined) return;
    setBusy("plan");
    setProblem(undefined);
    setSuccess(undefined);
    setPlan(undefined);
    const outcome = await postJson(
      `${base}/plan`,
      { concepts: conceptsFrom(conceptsText) },
      { locale }
    );
    setBusy(undefined);
    if (outcome.kind !== "ok") {
      setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
      return;
    }
    const next = parsePlan(outcome.data);
    if (next === undefined) {
      setProblem({ ...networkProblem(), code: "internal_error", status: 200 });
      return;
    }
    setPlan(next);
  }

  async function start(): Promise<void> {
    if (plan === undefined || busy !== undefined) return;
    setBusy("start");
    setProblem(undefined);
    setSuccess(undefined);
    const outcome = await postJson(
      base,
      { approved_digest: plan.digest, concepts: conceptsFrom(conceptsText) },
      { locale }
    );
    setBusy(undefined);
    setConfirmOpen(false);
    if (outcome.kind !== "ok") {
      setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
      return;
    }
    setSuccess(copy.started);
  }

  return (
    <div className="grid gap-4" data-slot="discovery-preview">
      <p className="m-0">{copy.body}</p>
      <p className="m-0 text-sm text-muted-foreground">{copy.private}</p>
      <Field controlId={`${id}-concepts`} description={copy.conceptsHint} label={copy.concepts}>
        <Input
          autoComplete="off"
          disabled={busy !== undefined}
          maxLength={1600}
          onChange={(event) => {
            setConceptsText(event.target.value);
            setPlan(undefined);
            setSuccess(undefined);
          }}
          value={conceptsText}
        />
      </Field>
      {plan === undefined ? (
        <div>
          <Button disabled={busy !== undefined} type="button" onClick={() => void prepare()}>
            {busy === "plan" ? copy.preparing : copy.prepare}
          </Button>
        </div>
      ) : (
        <div className="grid gap-3 border border-border bg-card p-3" data-slot="discovery-plan">
          <h3 className="m-0 text-base">{copy.planTitle}</h3>
          <Field controlId={`${id}-query`} description={copy.queryHint} label={copy.query}>
            <Textarea readOnly rows={3} value={plan.query} />
          </Field>
          <p className="m-0 text-sm">
            {copy.policy}: {plan.policyVersion}
          </p>
          <div className="grid gap-1">
            <strong>{copy.included}</strong>
            <ul className="m-0 grid gap-1 ps-5">
              {plan.terms.map((term) => (
                <li key={`${term.source}-${term.text}`}>
                  {term.text} <span className="text-muted-foreground">({term.source})</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="grid gap-1">
            <strong>{copy.excluded}</strong>
            {plan.rejected.length === 0 ? (
              <p className="m-0">{copy.noneExcluded}</p>
            ) : (
              <ul className="m-0 grid gap-1 ps-5">
                {plan.rejected.map((item) => (
                  <li key={`${item.source}-${item.reason}`}>
                    {item.source}: {item.reason}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={() => setConfirmOpen(true)}>
              {copy.approve}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setPlan(undefined);
                setSuccess(undefined);
              }}
            >
              {copy.discard}
            </Button>
          </div>
        </div>
      )}
      <ActionFeedback
        actions={actions}
        problem={problem}
        problems={problems}
        signInHref={signInHref}
        success={success}
      />
      <ConfirmDialog
        cancelLabel={copy.cancel}
        confirmLabel={copy.confirm}
        description={copy.confirmBody}
        onConfirm={() => void start()}
        onOpenChange={setConfirmOpen}
        open={confirmOpen}
        title={copy.confirmTitle}
      />
    </div>
  );
}
