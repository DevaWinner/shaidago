"use client";

import { useEffect, useId, useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { QuestionAnswer } from "@/components/project/question-answer";
import { Button, ButtonLink } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/field";
import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters } from "@/lib/format/formatters";
import { networkProblem, readBrowserProblem } from "@/lib/problems/browser-problem";
import { describeProblem, type SafeProblem } from "@/lib/problems/problem-messages";
import { QUESTION_MAX, interpretAnswer, type AnswerOutcome } from "@/lib/qa/answer";

type Phase =
  | Readonly<{ name: "idle" }>
  | Readonly<{ name: "loading" }>
  | Readonly<{ name: "cancelled" }>
  | Readonly<{ name: "answered"; outcome: Exclude<AnswerOutcome, { kind: "invalid" }> }>
  | Readonly<{ name: "failed"; problem: SafeProblem }>;

/** Hydration has no event to subscribe to: the server snapshot is `false` and the client's is `true`. */
function subscribeNever(): () => void {
  return () => undefined;
}

const INVALID_RESPONSE: SafeProblem = {
  code: "internal_error",
  status: 200,
  requestId: undefined,
  retryAfterSeconds: undefined,
  fieldErrors: []
};

/**
 * The one client island of a record page: a question box, a response region, and retry. The question
 * lives only in this component's memory: it is never put in a URL, storage, or a cache, and it is
 * sent only to the same-origin route handler. Nothing is asked automatically or on prefetch. A
 * failure never touches the rest of the page, which stays a plain server-rendered record.
 */
export function ProjectQuestion({
  base,
  copy,
  evidence,
  factsHref,
  language,
  locale,
  problems,
  reportHref,
  slug
}: Readonly<{
  base: string;
  copy: Messages["qa"];
  evidence: Messages["evidence"];
  factsHref: string;
  language: ApiLocale;
  locale: ApiLocale;
  problems: Messages["problems"];
  reportHref: string;
  slug: string;
}>): ReactNode {
  const controlId = useId();
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<Phase>({ name: "idle" });
  const [fieldError, setFieldError] = useState<string | undefined>(undefined);
  // Until hydration the button stays disabled, so a form can never fall back to a native submit
  // that would put the question in the address bar.
  const ready = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false
  );
  const inFlight = useRef<AbortController | undefined>(undefined);
  const format = createFormatters(language);

  useEffect(() => () => inFlight.current?.abort(), []);

  async function ask(): Promise<void> {
    if (inFlight.current !== undefined) {
      return;
    }

    const text = question.trim();

    if (text === "") {
      setFieldError(copy.empty);
      return;
    }
    if (text.length > QUESTION_MAX) {
      setFieldError(formatMessageLite(copy.tooLong, { max: QUESTION_MAX }));
      return;
    }

    setFieldError(undefined);
    const controller = new AbortController();
    inFlight.current = controller;
    setPhase({ name: "loading" });

    try {
      const response = await fetch("/api/public/questions", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Shaidago-Locale": locale
        },
        body: JSON.stringify({ slug, question: text }),
        cache: "no-store",
        credentials: "same-origin",
        signal: controller.signal
      });

      if (!response.ok) {
        setPhase({ name: "failed", problem: await readBrowserProblem(response) });
        return;
      }

      const outcome = interpretAnswer(await response.json());

      setPhase(
        outcome.kind === "invalid"
          ? {
              name: "failed",
              problem: {
                ...INVALID_RESPONSE,
                requestId: response.headers.get("X-Request-Id") ?? undefined
              }
            }
          : { name: "answered", outcome }
      );
    } catch (error) {
      if (
        controller.signal.aborted ||
        (error instanceof DOMException && error.name === "AbortError")
      ) {
        setPhase({ name: "cancelled" });
      } else if (error instanceof SyntaxError) {
        setPhase({ name: "failed", problem: INVALID_RESPONSE });
      } else {
        setPhase({ name: "failed", problem: networkProblem() });
      }
    } finally {
      if (inFlight.current === controller) {
        inFlight.current = undefined;
      }
    }
  }

  const loading = phase.name === "loading";
  const failure =
    phase.name === "failed"
      ? describeProblem(phase.problem, problems, formatMessageLite)
      : undefined;
  const announcement =
    phase.name === "loading"
      ? copy.loading
      : phase.name === "cancelled"
        ? copy.cancelled
        : phase.name === "answered"
          ? phase.outcome.kind === "supported"
            ? copy.result.ready
            : phase.outcome.kind === "insufficient"
              ? copy.insufficient.title
              : copy.rejected.title
          : failure === undefined
            ? ""
            : failure.message;

  return (
    <section
      aria-labelledby={`${controlId}-heading`}
      className="grid gap-4"
      data-slot="project-question"
    >
      <h3 className="m-0 text-ledger-lg" id={`${controlId}-heading`}>
        {copy.heading}
      </h3>
      <p className="m-0 max-w-[68ch]">{copy.intro}</p>
      <p className="m-0 max-w-[68ch] text-sm text-muted-foreground">
        {copy.privacy}{" "}
        <a className="font-semibold text-ledger-accent-strong underline" href={reportHref}>
          {copy.reportLink}
        </a>
      </p>
      <form
        className="grid max-w-[68ch] gap-3"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void ask();
        }}
      >
        <Field
          controlId={controlId}
          description={`${formatMessageLite(copy.hint, { max: QUESTION_MAX })} ${formatMessageLite(
            copy.counter,
            { count: question.length, max: QUESTION_MAX }
          )}`}
          error={fieldError}
          label={copy.label}
        >
          <Textarea
            autoComplete="off"
            maxLength={QUESTION_MAX}
            onChange={(event) => {
              setQuestion(event.target.value);
              setFieldError(undefined);
            }}
            readOnly={loading}
            rows={3}
            value={question}
          />
        </Field>
        <div className="flex flex-wrap items-center gap-3">
          <Button aria-disabled={loading || !ready} disabled={!ready} type="submit">
            {phase.name === "failed" || phase.name === "cancelled" ? copy.retry : copy.submit}
          </Button>
          {loading ? (
            <Button onClick={() => inFlight.current?.abort()} variant="secondary">
              {copy.cancel}
            </Button>
          ) : null}
        </div>
        <p className="m-0 text-sm" hidden={ready}>
          {copy.needsScript}
        </p>
      </form>
      <p
        aria-live="polite"
        className={loading ? "m-0" : "sr-only"}
        data-slot="question-status"
        role="status"
      >
        {announcement}
      </p>
      <div data-slot="question-result">
        {phase.name === "answered" ? (
          <QuestionAnswer
            base={base}
            copy={copy}
            evidence={evidence}
            factsHref={factsHref}
            format={format}
            outcome={phase.outcome}
          />
        ) : null}
        {failure === undefined || phase.name !== "failed" ? null : (
          <div className="grid max-w-[68ch] gap-2 border-2 border-destructive bg-card p-4">
            <h4 className="m-0 text-ledger-lg">{copy.failure.title}</h4>
            <p className="m-0">{failure.message}</p>
            {phase.problem.retryAfterSeconds === undefined ? null : (
              <p className="m-0">
                {formatMessageLite(copy.failure.wait, { seconds: phase.problem.retryAfterSeconds })}
              </p>
            )}
            {failure.referenceLine === undefined ? null : (
              <p className="m-0 text-sm">{failure.referenceLine}</p>
            )}
            <p className="m-0 text-sm text-muted-foreground">{copy.failure.still}</p>
            <div>
              <ButtonLink href={factsHref} variant="secondary">
                {copy.insufficient.read}
              </ButtonLink>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
