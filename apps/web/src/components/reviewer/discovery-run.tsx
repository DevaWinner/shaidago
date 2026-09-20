"use client";

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";

import {
  AnalysisSections,
  RunOutcome,
  RunSummary,
  SourceList,
  UnreviewedLabel,
  type DiscoveryCopy
} from "@/components/discovery/results";
import { ActionFeedback } from "@/components/reviewer/action-feedback";
import { Button } from "@/components/ui/button";
import { Callout, LiveRegion } from "@/components/ui/feedback";
import { Field, Textarea } from "@/components/ui/field";
import { ConfirmDialog } from "@/components/ui/overlay";
import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { parseRun, type RunView, type SourceView } from "@/lib/discovery/parse";
import {
  allowedDiscoveryActions,
  isNewerRunSnapshot,
  nextPollDelayMs,
  shouldPoll
} from "@/lib/discovery/run-state";
import { createFormatters } from "@/lib/format/formatters";
import { scaleDelay } from "@/lib/low-data";
import { networkProblem, readBrowserProblem } from "@/lib/problems/browser-problem";
import type { SafeProblem } from "@/lib/problems/problem-messages";
import { postJson } from "@/lib/tracking/client";

type Shared = Readonly<{
  actions: Messages["reviewer"]["actions"];
  copy: DiscoveryCopy;
  locale: ApiLocale;
  problems: Messages["problems"];
  runId: string;
  signInHref: string;
}>;

const INVALID: SafeProblem = {
  code: "internal_error",
  status: 200,
  requestId: undefined,
  retryAfterSeconds: undefined,
  fieldErrors: []
};

const ANSWER_MAX = 2000;
const REASON_MAX = 400;

/** What the source-decision state machine allows from a disposition (contract, `discovered_source_disposition`). */
const DECISIONS: Readonly<
  Record<string, readonly ("attach" | "reject" | "defer" | "reconsider")[]>
> = {
  not_reviewed: ["attach", "reject", "defer"],
  deferred: ["attach", "reject"],
  attached: ["reconsider"],
  rejected: ["reconsider"]
};

function FollowUp({
  index,
  question,
  shared
}: Readonly<{
  index: number;
  question: Readonly<{ question: string; reason: string; sensitivity: string }>;
  shared: Shared;
}>): ReactNode {
  const id = useId();
  const words = shared.copy.followUps;
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const [done, setDone] = useState<string | undefined>(undefined);
  const [pending, setPending] = useState(false);
  // The run this question was rendered for; an answer is never sent for another run.
  const boundRun = useRef(shared.runId);

  async function send(kind: "answered" | "skipped" | "unsafe"): Promise<void> {
    if (pending || done !== undefined) return;
    if (boundRun.current !== shared.runId) {
      setError(words.stale);
      return;
    }
    if (kind === "answered" && answer.trim() === "") {
      setError(words.required);
      return;
    }
    if (answer.length > ANSWER_MAX) {
      setError(words.tooLong);
      return;
    }
    setError(undefined);
    setProblem(undefined);
    setPending(true);
    const outcome = await postJson(
      `/api/reviewer/discovery/${encodeURIComponent(shared.runId)}/follow-up-answers`,
      {
        question_index: index,
        kind,
        ...(kind === "answered" ? { answer: answer.trim() } : {})
      },
      { locale: shared.locale }
    );

    setPending(false);
    if (outcome.kind === "ok") {
      // Only a safe acknowledgement is kept; the typed answer is dropped from memory.
      setAnswer("");
      setDone(
        kind === "answered" ? words.sent : kind === "skipped" ? words.skipped : words.flagged
      );
      return;
    }
    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
  }

  return (
    <li className="grid gap-2 border border-border bg-card p-3" data-slot="discovery-follow-up">
      <strong className="[overflow-wrap:anywhere]">{question.question}</strong>
      <small>{formatMessageLite(words.why, { reason: question.reason })}</small>
      <small>{formatMessageLite(words.sensitivity, { level: question.sensitivity })}</small>
      {done !== undefined ? (
        <p className="m-0 font-semibold" role="status">
          {done}
        </p>
      ) : (
        <>
          <Field
            controlId={`${id}-answer`}
            description={words.answerHint}
            error={error}
            label={words.answerLabel}
          >
            <Textarea
              autoComplete="off"
              onChange={(event) => {
                setAnswer(event.target.value);
              }}
              rows={3}
              value={answer}
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button
              aria-disabled={pending}
              onClick={() => {
                void send("answered");
              }}
            >
              {words.send}
            </Button>
            <Button
              aria-disabled={pending}
              onClick={() => {
                void send("skipped");
              }}
              variant="secondary"
            >
              {words.skip}
            </Button>
            <Button
              aria-disabled={pending}
              onClick={() => {
                void send("unsafe");
              }}
              variant="secondary"
            >
              {words.unsafe}
            </Button>
          </div>
        </>
      )}
      <ActionFeedback
        actions={shared.actions}
        problem={problem}
        problems={shared.problems}
        signInHref={shared.signInHref}
        success={undefined}
      />
    </li>
  );
}

function SourceDecision({
  onDecided,
  shared,
  source
}: Readonly<{ onDecided: () => void; shared: Shared; source: SourceView }>): ReactNode {
  const id = useId();
  const words = shared.copy.decisions;
  const options = DECISIONS[source.disposition ?? "not_reviewed"] ?? [];
  const [command, setCommand] = useState<(typeof options)[number] | undefined>(undefined);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const [note, setNote] = useState<string | undefined>(undefined);
  const [pending, setPending] = useState(false);
  const label = (table: object, key: string): string =>
    (table as Readonly<Record<string, string | undefined>>)[key] ?? key;

  async function send(chosen: string): Promise<void> {
    setPending(true);
    const outcome = await postJson(
      `/api/reviewer/discovered-sources/${encodeURIComponent(source.id)}/decision`,
      { command: chosen, reason: reason.trim() },
      { locale: shared.locale }
    );

    setPending(false);
    setCommand(undefined);
    if (outcome.kind === "ok") {
      setReason("");
      setNote(undefined);
      onDecided();
      return;
    }
    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
    if (outcome.kind === "problem" && outcome.problem.status === 409) {
      onDecided();
    }
  }

  return (
    <div className="grid gap-2 border-t border-border pt-2" data-slot="discovery-decision">
      <p className="m-0 text-sm font-semibold">
        {shared.copy.card.decision}:{" "}
        {label(words.dispositions, source.disposition ?? "not_reviewed")}
      </p>
      {options.length === 0 ? null : (
        <>
          <Field
            controlId={`${id}-reason`}
            description={words.reasonHint}
            error={error}
            label={words.reason}
          >
            <Textarea
              autoComplete="off"
              onChange={(event) => {
                setReason(event.target.value);
              }}
              rows={2}
              value={reason}
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            {options.map((option) => (
              <Button
                aria-disabled={pending}
                key={option}
                onClick={() => {
                  if (pending) return;
                  setProblem(undefined);
                  if (reason.trim() === "") {
                    setError(words.reasonRequired);
                    return;
                  }
                  if (reason.length > REASON_MAX) {
                    setError(words.reasonTooLong);
                    return;
                  }
                  setError(undefined);
                  setCommand(option);
                }}
                variant="secondary"
              >
                {words[option]}
              </Button>
            ))}
          </div>
        </>
      )}
      <ConfirmDialog
        cancelLabel={words.cancel}
        confirmLabel={words.confirm}
        description={command === undefined ? "" : label(words, `${command}Body`)}
        onConfirm={() => {
          if (command !== undefined) void send(command);
        }}
        onOpenChange={(open) => {
          if (!open) setCommand(undefined);
        }}
        open={command !== undefined}
        title={words.confirmTitle}
      />
      {problem?.status === 409 ? (
        <p className="m-0 font-semibold" role="alert">
          {words.conflict}
        </p>
      ) : (
        <ActionFeedback
          actions={shared.actions}
          problem={problem}
          problems={shared.problems}
          signInHref={shared.signInHref}
          success={note}
        />
      )}
    </div>
  );
}

/**
 * Follows one report-scoped run, and only that run: the run ID is fixed for the life of this
 * component, a response for another run, scope, or an older version is ignored, and nothing about
 * the run is stored anywhere but this component's memory. It polls only while the run is active,
 * pauses when the tab is hidden or the browser is offline (keeping what is already shown), and
 * stops for good at a terminal status. Cancelling and review are requests; the API decides.
 */
export function DiscoveryRun({
  actions,
  copy,
  locale,
  problems,
  runId,
  signInHref
}: Shared): ReactNode {
  const shared: Shared = { actions, copy, locale, problems, runId, signInHref };
  const format = createFormatters(locale);
  const [run, setRun] = useState<RunView | undefined>(undefined);
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const [online, setOnline] = useState(true);
  const [paused, setPaused] = useState(false);
  const [note, setNote] = useState<string | undefined>(undefined);
  const [confirm, setConfirm] = useState<"cancel" | "approve" | "reject" | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  const attempts = useRef(0);
  const current = useRef<RunView | undefined>(undefined);
  const controller = useRef<AbortController | undefined>(undefined);

  const load = useCallback(
    async (force: boolean): Promise<void> => {
      controller.current?.abort();
      const next = new AbortController();

      controller.current = next;
      const known = force ? undefined : current.current;

      try {
        const response = await fetch(
          `/api/reviewer/discovery/${encodeURIComponent(runId)}${known === undefined ? "" : `?since_version=${known.version}`}`,
          {
            cache: "no-store",
            credentials: "same-origin",
            headers: { Accept: "application/json", "X-Shaidago-Locale": locale },
            signal: next.signal
          }
        );

        if (response.status === 304) return;
        if (!response.ok) {
          setProblem(await readBrowserProblem(response));
          return;
        }

        const parsed = parseRun(await response.json(), "reviewer");

        if (parsed === undefined || parsed.runId !== runId) {
          setProblem(INVALID);
          return;
        }
        if (
          known !== undefined &&
          !isNewerRunSnapshot(
            { runId, scope: "reviewer", version: known.version },
            { runId: parsed.runId, scope: "reviewer", version: parsed.version }
          ) &&
          parsed.version !== known.version
        ) {
          return;
        }

        current.current = parsed;
        setStale(
          parsed.finishedAt !== null &&
            Date.now() - Date.parse(parsed.finishedAt) > 24 * 60 * 60 * 1000
        );
        setProblem(undefined);
        setRun(parsed);
      } catch (error) {
        if (!next.signal.aborted) {
          setProblem(error instanceof SyntaxError ? INVALID : networkProblem());
        }
      }
    },
    [locale, runId]
  );

  useEffect(() => {
    void load(true);

    return () => {
      controller.current?.abort();
    };
  }, [load]);

  useEffect(() => {
    const update = (): void => {
      setOnline(navigator.onLine);
    };

    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);

    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const version = run?.version;
  const active = run !== undefined && !paused && shouldPoll("reviewer", run.status);

  useEffect(() => {
    if (!active || !online) return;
    const retry = problem?.retryAfterSeconds;
    const timer = window.setTimeout(
      () => {
        if (document.hidden) return;
        attempts.current += 1;
        void load(false);
      },
      scaleDelay(nextPollDelayMs(attempts.current, retry))
    );

    return () => {
      window.clearTimeout(timer);
    };
  }, [active, online, load, version, problem]);

  async function act(kind: "cancel" | "approve" | "reject"): Promise<void> {
    setConfirm(undefined);
    setBusy(true);
    setNote(undefined);
    const base = `/api/reviewer/discovery/${encodeURIComponent(runId)}`;
    const outcome =
      kind === "cancel"
        ? await postJson(`${base}/cancel`, undefined, { locale })
        : await postJson(
            `${base}/review`,
            { command: kind === "approve" ? "approve_completion" : "reject_run" },
            { locale }
          );

    setBusy(false);
    if (outcome.kind === "ok") {
      setNote(kind === "cancel" ? copy.controls.cancelRequested : copy.controls.reviewed);
      attempts.current = 0;
      await load(true);
      return;
    }
    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
  }

  if (run === undefined) {
    return (
      <div className="grid gap-2" data-slot="discovery-run">
        <LiveRegion>{copy.states.checking}</LiveRegion>
        {problem === undefined ? (
          <p className="m-0" role="status">
            {copy.states.checking}
          </p>
        ) : (
          <>
            <ActionFeedback
              actions={actions}
              problem={problem}
              problems={problems}
              signInHref={signInHref}
              success={undefined}
            />
            <div>
              <Button
                onClick={() => {
                  void load(true);
                }}
                variant="secondary"
              >
                {copy.controls.retry}
              </Button>
            </div>
          </>
        )}
      </div>
    );
  }

  const allowed = allowedDiscoveryActions("reviewer", run.status, run.cancelRequested);
  const decidable = !shouldPoll("reviewer", run.status);

  return (
    <div className="grid gap-4" data-slot="discovery-run" data-status={run.status}>
      <UnreviewedLabel copy={copy} />
      <p className="m-0 text-sm">{copy.unreviewedNote}</p>
      <RunSummary copy={copy} format={format} run={run} />
      <LiveRegion>
        {copy.status.states[run.status as keyof typeof copy.status.states] ?? ""}
      </LiveRegion>
      {online ? null : (
        <Callout title={copy.states.offline} tone="warning">
          {null}
        </Callout>
      )}
      {stale ? (
        <p className="m-0 text-sm" role="status">
          {formatMessageLite(copy.states.stale, {
            date: format.dateTime(run.finishedAt ?? run.createdAt)
          })}
        </p>
      ) : null}
      {problem === undefined ? null : (
        <div className="grid gap-2">
          <ActionFeedback
            actions={actions}
            problem={problem}
            problems={problems}
            signInHref={signInHref}
            success={undefined}
          />
          <div>
            <Button
              onClick={() => {
                attempts.current = 0;
                void load(true);
              }}
              variant="secondary"
            >
              {copy.controls.retry}
            </Button>
          </div>
        </div>
      )}
      {run.cancelRequested && shouldPoll("reviewer", run.status) ? (
        <p className="m-0 font-semibold" role="status">
          {copy.controls.cancelRequested}
        </p>
      ) : null}
      {run.status === "needs_review" ? (
        <Callout title={copy.states.needsReview} tone="warning">
          {null}
        </Callout>
      ) : null}
      <RunOutcome copy={copy} run={run} />
      <div className="flex flex-wrap gap-2">
        {allowed.includes("cancel") ? (
          <Button
            aria-disabled={busy}
            onClick={() => {
              setConfirm("cancel");
            }}
            variant="secondary"
          >
            {copy.controls.cancel}
          </Button>
        ) : null}
        {allowed.includes("review") ? (
          <>
            <Button
              aria-disabled={busy}
              onClick={() => {
                setConfirm("approve");
              }}
            >
              {copy.controls.approve}
            </Button>
            <Button
              aria-disabled={busy}
              onClick={() => {
                setConfirm("reject");
              }}
              variant="secondary"
            >
              {copy.controls.reject}
            </Button>
          </>
        ) : null}
        {shouldPoll("reviewer", run.status) ? (
          <Button
            onClick={() => {
              setPaused((value) => !value);
            }}
            variant="secondary"
          >
            {paused ? copy.controls.resumeChecking : copy.controls.stopChecking}
          </Button>
        ) : null}
      </div>
      <ConfirmDialog
        cancelLabel={confirm === "cancel" ? copy.controls.keep : copy.decisions.cancel}
        confirmLabel={
          confirm === "cancel" ? copy.controls.cancelConfirm : copy.controls.reviewConfirm
        }
        description={
          confirm === "cancel"
            ? copy.controls.cancelBody
            : confirm === "approve"
              ? copy.controls.approveBody
              : copy.controls.rejectBody
        }
        onConfirm={() => {
          if (confirm !== undefined) void act(confirm);
        }}
        onOpenChange={(open) => {
          if (!open) setConfirm(undefined);
        }}
        open={confirm !== undefined}
        title={confirm === "cancel" ? copy.controls.cancelTitle : copy.controls.reviewTitle}
      />
      {note === undefined ? null : (
        <p className="m-0 font-semibold" role="status">
          {note}
        </p>
      )}
      <section aria-label={copy.results.heading} className="grid gap-3">
        <h3 className="m-0 text-base">{copy.results.heading}</h3>
        <p className="m-0 text-sm">
          {formatMessageLite(copy.results.count, { count: run.sources.length })} ·{" "}
          {copy.results.cap}
        </p>
        <SourceList
          copy={copy}
          format={format}
          renderExtra={
            decidable
              ? (source) => (
                  <SourceDecision
                    onDecided={() => {
                      void load(true);
                    }}
                    shared={shared}
                    source={source}
                  />
                )
              : undefined
          }
          sources={run.sources}
        />
      </section>
      {run.status === "complete" || run.status === "needs_review" ? (
        <>
          <AnalysisSections analysis={run.analysis} copy={copy} sources={run.sources} />
          {run.analysis === undefined ? null : (
            <section aria-label={copy.followUps.heading} className="grid gap-2">
              <h3 className="m-0 text-base">{copy.followUps.heading}</h3>
              <p className="m-0 text-sm">{copy.followUps.cap}</p>
              {run.analysis.followUps.length === 0 ? (
                <p className="m-0">{copy.followUps.none}</p>
              ) : (
                <ol className="m-0 grid list-none gap-3 p-0">
                  {run.analysis.followUps.map((question, index) => (
                    <FollowUp
                      index={index}
                      key={`${runId}-${index}`}
                      question={question}
                      shared={shared}
                    />
                  ))}
                </ol>
              )}
            </section>
          )}
        </>
      ) : null}
    </div>
  );
}
