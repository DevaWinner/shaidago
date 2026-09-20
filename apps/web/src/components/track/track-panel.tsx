"use client";

import { useEffect, useId, useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input, Textarea } from "@/components/ui/field";
import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { createFormatters } from "@/lib/format/formatters";
import { describeProblem, type SafeProblem } from "@/lib/problems/problem-messages";
import { CODE_MAX, normaliseCode } from "@/lib/tracking/normalise";
import {
  parseAck,
  parseHandleReports,
  parseStatus,
  postJson,
  type HandleItem,
  type NextAction,
  type QuestionState,
  type ReportStatus,
  type StatusView
} from "@/lib/tracking/client";

type Copy = Messages["track"];

type Load<T> =
  | Readonly<{ phase: "idle" }>
  | Readonly<{ phase: "loading" }>
  | Readonly<{ phase: "ok"; data: T }>
  | Readonly<{ phase: "failed"; problem: SafeProblem }>;

const INVALID: SafeProblem = {
  code: "internal_error",
  status: 200,
  requestId: undefined,
  retryAfterSeconds: undefined,
  fieldErrors: []
};

function subscribeNever(): () => void {
  return () => undefined;
}

function StatusBlock({
  copy,
  format,
  message,
  next,
  status,
  updatedAt
}: Readonly<{
  copy: Copy;
  format: ReturnType<typeof createFormatters>;
  message: string;
  next: NextAction | undefined;
  status: ReportStatus;
  updatedAt: string;
}>): ReactNode {
  const text = copy.statuses[status];

  return (
    <div className="grid gap-2">
      <p className="m-0 text-ledger-lg font-bold">
        {copy.result.heading}: {text.label}
      </p>
      <p className="m-0">{text.meaning}</p>
      <p className="m-0 text-sm text-muted-foreground">
        {formatMessageLite(copy.result.updated, { date: format.dateTime(updatedAt) })}
      </p>
      {message === "" ? null : (
        <p className="m-0 text-sm [overflow-wrap:anywhere]">
          <strong>{copy.result.message}:</strong> {message}
        </p>
      )}
      {next === undefined ? null : (
        <p className="m-0">
          <strong>{copy.result.nextHeading}:</strong> {copy.next[next]}
        </p>
      )}
    </div>
  );
}

function FailureBox({
  copy,
  problem,
  problems
}: Readonly<{ copy: Copy; problem: SafeProblem; problems: Messages["problems"] }>): ReactNode {
  const view = describeProblem(problem, problems, formatMessageLite);

  return (
    <div className="grid gap-2 border-2 border-destructive bg-card p-4" data-slot="track-failure">
      <h3 className="m-0 text-ledger-lg">{copy.failure.title}</h3>
      <p className="m-0">{view.message}</p>
      {problem.retryAfterSeconds === undefined ? null : (
        <p className="m-0">
          {formatMessageLite(copy.failure.wait, { seconds: problem.retryAfterSeconds })}
        </p>
      )}
      {view.referenceLine === undefined ? null : (
        <p className="m-0 text-sm">{view.referenceLine}</p>
      )}
      <p className="m-0 text-sm text-muted-foreground">{copy.failure.still}</p>
    </div>
  );
}

/**
 * Status by tracking code or by reporter handle. Credentials live only in this component's memory:
 * they are sent in POST bodies, never shown back, never stored, and never put in the address. Every
 * miss (unknown code, wrong handle, wrong passphrase) is the same generic message, so the page
 * cannot be used to learn whether a report or handle exists.
 */
export function TrackPanel({
  copy,
  language,
  locale,
  problems,
  reportHref
}: Readonly<{
  copy: Copy;
  language: ApiLocale;
  locale: ApiLocale;
  problems: Messages["problems"];
  reportHref: string;
}>): ReactNode {
  const id = useId();
  const format = createFormatters(language);
  const ready = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false
  );
  const [codeInput, setCodeInput] = useState("");
  const [codeError, setCodeError] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState<Load<StatusView>>({ phase: "idle" });
  const [handleInput, setHandleInput] = useState("");
  const [passInput, setPassInput] = useState("");
  const [reveal, setReveal] = useState(false);
  const [handleError, setHandleError] = useState<{ handle?: string; pass?: string }>({});
  const [reports, setReports] = useState<Load<readonly HandleItem[]>>({ phase: "idle" });
  const [answering, setAnswering] = useState<Readonly<Record<string, string>>>({});
  const [sent, setSent] = useState<Readonly<Record<string, boolean>>>({});
  const [followFailure, setFollowFailure] = useState<SafeProblem | undefined>(undefined);
  const [followNote, setFollowNote] = useState<string | undefined>(undefined);
  const [hasCode, setHasCode] = useState(false);
  const code = useRef<string | undefined>(undefined);
  const credentials = useRef<{ handle: string; passphrase: string } | undefined>(undefined);
  const busy = useRef<AbortController | undefined>(undefined);
  const keys = useRef<Map<string, string>>(new Map());
  const codeResult = useRef<HTMLHeadingElement>(null);
  const listResult = useRef<HTMLHeadingElement>(null);

  useEffect(() => () => busy.current?.abort(), []);
  useEffect(() => {
    if (status.phase === "ok" || status.phase === "failed") {
      codeResult.current?.focus();
    }
  }, [status.phase]);
  useEffect(() => {
    if (reports.phase === "ok" || reports.phase === "failed") {
      listResult.current?.focus();
    }
  }, [reports.phase]);

  async function lookup(value: string): Promise<void> {
    if (busy.current !== undefined) {
      return;
    }

    const active = new AbortController();

    busy.current = active;
    setStatus({ phase: "loading" });
    setFollowFailure(undefined);

    const outcome = await postJson(
      "/api/tracking/lookup",
      { code: value },
      { locale, signal: active.signal }
    );

    busy.current = undefined;

    if (outcome.kind === "aborted") {
      setStatus({ phase: "idle" });
    } else if (outcome.kind === "network") {
      setStatus({
        phase: "failed",
        problem: { ...INVALID, code: "network_unavailable", status: undefined }
      });
    } else if (outcome.kind === "problem") {
      code.current = undefined;
      setHasCode(false);
      setStatus({ phase: "failed", problem: outcome.problem });
    } else {
      const parsed = parseStatus(outcome.data);

      if (parsed === undefined) {
        setStatus({ phase: "failed", problem: INVALID });
      } else {
        // The code stays in memory for follow-up answers, and the box no longer shows it.
        code.current = value;
        setHasCode(true);
        setCodeInput("");
        setStatus({ phase: "ok", data: parsed });
      }
    }
  }

  function submitCode(): void {
    const value = normaliseCode(codeInput);

    if (value === "" || value.length > CODE_MAX) {
      setCodeError(copy.code.empty);
      return;
    }
    setCodeError(undefined);
    void lookup(value);
  }

  async function listReports(given: { handle: string; passphrase: string }): Promise<void> {
    if (busy.current !== undefined) {
      return;
    }

    const active = new AbortController();

    busy.current = active;
    setReports({ phase: "loading" });

    const outcome = await postJson("/api/reporter-handle/reports", given, {
      locale,
      signal: active.signal
    });

    busy.current = undefined;

    if (outcome.kind === "aborted") {
      setReports({ phase: "idle" });
    } else if (outcome.kind === "network") {
      setReports({
        phase: "failed",
        problem: { ...INVALID, code: "network_unavailable", status: undefined }
      });
    } else if (outcome.kind === "problem") {
      credentials.current = undefined;
      setReports({ phase: "failed", problem: outcome.problem });
    } else {
      const parsed = parseHandleReports(outcome.data);

      if (parsed === undefined) {
        setReports({ phase: "failed", problem: INVALID });
      } else {
        credentials.current = given;
        setPassInput("");
        setReveal(false);
        setReports({ phase: "ok", data: parsed });
      }
    }
  }

  function submitHandle(): void {
    const errors = {
      ...(handleInput.trim() === "" ? { handle: copy.handle.emptyHandle } : {}),
      ...(passInput === "" ? { pass: copy.handle.emptyPassphrase } : {})
    };

    setHandleError(errors);
    if (Object.keys(errors).length === 0) {
      void listReports({ handle: handleInput.trim(), passphrase: passInput });
    }
  }

  async function respond(question: string, kind: "answered" | "skipped" | "unsafe"): Promise<void> {
    if (code.current === undefined || status.phase !== "ok") {
      return;
    }

    const answer = (answering[question] ?? "").trim();

    setFollowNote(undefined);

    if (kind === "answered" && answer === "") {
      setFollowNote(copy.followUp.answerEmpty);
      return;
    }

    // One key per exact response, reused on a retry of it, so a repeat cannot answer twice.
    const signature = JSON.stringify([question, kind, kind === "answered" ? answer : ""]);
    let key = keys.current.get(signature);

    if (key === undefined) {
      key = crypto.randomUUID();
      keys.current.set(signature, key);
    }

    const outcome = await postJson(
      "/api/tracking/follow-up",
      {
        question_id: question,
        kind,
        code: code.current,
        ...(kind === "answered" ? { answer } : {})
      },
      { locale, idempotencyKey: key }
    );

    if (outcome.kind === "ok") {
      const state = parseAck(outcome.data);

      if (state === undefined) {
        setFollowFailure(INVALID);
        return;
      }
      setFollowFailure(undefined);
      setSent((current) => ({ ...current, [question]: true }));
      setAnswering((current) => ({ ...current, [question]: "" }));
      setStatus({
        phase: "ok",
        data: {
          ...status.data,
          questions: status.data.questions.map((item) =>
            item.id === question ? { ...item, state: state as QuestionState } : item
          )
        }
      });
    } else if (outcome.kind === "problem") {
      setFollowFailure(outcome.problem);
    } else if (outcome.kind === "network") {
      setFollowFailure({ ...INVALID, code: "network_unavailable", status: undefined });
    }
  }

  function clearCode(): void {
    code.current = undefined;
    setHasCode(false);
    setFollowNote(undefined);
    setCodeInput("");
    setCodeError(undefined);
    setStatus({ phase: "idle" });
    setAnswering({});
    setSent({});
    setFollowFailure(undefined);
  }

  function clearHandle(): void {
    credentials.current = undefined;
    setHandleInput("");
    setPassInput("");
    setHandleError({});
    setReports({ phase: "idle" });
  }

  const loading = status.phase === "loading" || reports.phase === "loading";
  const announcement = loading
    ? copy.loading
    : status.phase === "ok"
      ? copy.statuses[status.data.status].label
      : status.phase === "failed"
        ? describeProblem(status.problem, problems, formatMessageLite).message
        : reports.phase === "ok"
          ? reports.data.length === 0
            ? copy.handle.none
            : copy.handle.listHeading
          : reports.phase === "failed"
            ? describeProblem(reports.problem, problems, formatMessageLite).message
            : "";
  const section = "grid gap-4 border-t border-border pt-8";

  return (
    <div className="grid max-w-[68ch] gap-8" data-slot="track-panel">
      <p className="m-0 text-sm text-muted-foreground" hidden={ready}>
        {copy.needsScript}
      </p>
      <p className="m-0 text-sm text-muted-foreground">{copy.privacy}</p>

      <section aria-labelledby={`${id}-code`} className={section}>
        <h2 className="m-0 text-ledger-xl" id={`${id}-code`}>
          {copy.code.heading}
        </h2>
        <form
          className="grid gap-3"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            submitCode();
          }}
        >
          <Field
            controlId={`${id}-code-input`}
            description={copy.code.hint}
            error={codeError}
            label={copy.code.label}
          >
            <Input
              autoCapitalize="off"
              autoComplete="off"
              autoCorrect="off"
              maxLength={CODE_MAX}
              onChange={(event) => setCodeInput(event.target.value)}
              readOnly={status.phase === "loading"}
              spellCheck={false}
              value={codeInput}
            />
          </Field>
          <div className="flex flex-wrap gap-3">
            <Button aria-disabled={!ready} disabled={!ready} type="submit">
              {copy.code.submit}
            </Button>
            {!hasCode ? null : (
              <Button onClick={() => void lookup(code.current as string)} variant="secondary">
                {copy.code.again}
              </Button>
            )}
            {status.phase === "idle" && codeInput === "" ? null : (
              <Button onClick={clearCode} variant="secondary">
                {copy.code.forget}
              </Button>
            )}
          </div>
        </form>
        {status.phase === "ok" || status.phase === "failed" ? (
          <div className="grid gap-3" data-slot="track-result">
            <h3 className="m-0 text-ledger-lg" ref={codeResult} tabIndex={-1}>
              {copy.result.heading}
            </h3>
            {status.phase === "failed" ? (
              <FailureBox copy={copy} problem={status.problem} problems={problems} />
            ) : (
              <>
                <StatusBlock
                  copy={copy}
                  format={format}
                  message={status.data.message}
                  next={status.data.nextAction}
                  status={status.data.status}
                  updatedAt={status.data.updatedAt}
                />
                {status.data.questions.length === 0 ? null : (
                  <section aria-labelledby={`${id}-fu`} className="grid gap-3">
                    <h4 className="m-0 text-ledger-lg" id={`${id}-fu`}>
                      {copy.followUp.heading}
                    </h4>
                    <p className="m-0 text-sm text-muted-foreground">{copy.followUp.intro}</p>
                    <ol className="m-0 grid list-none gap-4 p-0">
                      {status.data.questions.map((question) => (
                        <li
                          className="grid gap-2 border border-border bg-card p-3"
                          key={question.id}
                        >
                          <p className="m-0 font-semibold [overflow-wrap:anywhere]">
                            {question.text}
                          </p>
                          <p className="m-0 text-sm text-muted-foreground">
                            {copy.followUp.states[question.state]}
                          </p>
                          {question.state !== "open" ? null : (
                            <div className="grid gap-2">
                              <Field
                                controlId={`${id}-a-${question.id}`}
                                description={formatMessageLite(copy.followUp.counter, {
                                  count: (answering[question.id] ?? "").length,
                                  max: 2500
                                })}
                                label={copy.followUp.answerLabel}
                              >
                                <Textarea
                                  autoComplete="off"
                                  maxLength={2500}
                                  onChange={(event) =>
                                    setAnswering((current) => ({
                                      ...current,
                                      [question.id]: event.target.value
                                    }))
                                  }
                                  rows={4}
                                  value={answering[question.id] ?? ""}
                                />
                              </Field>
                              <div className="flex flex-wrap gap-3">
                                <Button onClick={() => void respond(question.id, "answered")}>
                                  {copy.followUp.answer}
                                </Button>
                                <Button
                                  onClick={() => void respond(question.id, "skipped")}
                                  variant="secondary"
                                >
                                  {copy.followUp.skip}
                                </Button>
                                <Button
                                  onClick={() => void respond(question.id, "unsafe")}
                                  variant="secondary"
                                >
                                  {copy.followUp.unsafe}
                                </Button>
                              </div>
                            </div>
                          )}
                          {sent[question.id] === true ? (
                            <p className="m-0 text-sm" role="status">
                              {copy.followUp.sent}
                            </p>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                    {followNote === undefined ? null : (
                      <p className="m-0 font-semibold text-destructive" role="alert">
                        {followNote}
                      </p>
                    )}
                    {followFailure === undefined ? null : (
                      <FailureBox copy={copy} problem={followFailure} problems={problems} />
                    )}
                  </section>
                )}
              </>
            )}
          </div>
        ) : null}
      </section>

      <section aria-labelledby={`${id}-handle`} className={section}>
        <h2 className="m-0 text-ledger-xl" id={`${id}-handle`}>
          {copy.handle.heading}
        </h2>
        <p className="m-0 text-sm text-muted-foreground">{copy.handle.note}</p>
        <form
          className="grid gap-3"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            submitHandle();
          }}
        >
          <Field
            controlId={`${id}-handle-input`}
            error={handleError.handle}
            label={copy.handle.handleLabel}
          >
            <Input
              autoCapitalize="off"
              autoComplete="off"
              maxLength={64}
              onChange={(event) => setHandleInput(event.target.value)}
              spellCheck={false}
              value={handleInput}
            />
          </Field>
          <Field
            controlId={`${id}-pass-input`}
            error={handleError.pass}
            label={copy.handle.passphraseLabel}
          >
            <Input
              autoCapitalize="off"
              autoComplete="off"
              maxLength={200}
              onChange={(event) => setPassInput(event.target.value)}
              spellCheck={false}
              type={reveal ? "text" : "password"}
              value={passInput}
            />
          </Field>
          <div className="flex flex-wrap gap-3">
            <Button aria-disabled={!ready} disabled={!ready} type="submit">
              {copy.handle.submit}
            </Button>
            <Button
              aria-pressed={reveal}
              onClick={() => setReveal((value) => !value)}
              variant="secondary"
            >
              {reveal ? copy.handle.hide : copy.handle.reveal}
            </Button>
            {reports.phase === "idle" && handleInput === "" && passInput === "" ? null : (
              <Button onClick={clearHandle} variant="secondary">
                {copy.handle.forget}
              </Button>
            )}
          </div>
        </form>
        {reports.phase === "ok" || reports.phase === "failed" ? (
          <div className="grid gap-3" data-slot="handle-result">
            <h3 className="m-0 text-ledger-lg" ref={listResult} tabIndex={-1}>
              {copy.handle.listHeading}
            </h3>
            {reports.phase === "failed" ? (
              <FailureBox copy={copy} problem={reports.problem} problems={problems} />
            ) : reports.data.length === 0 ? (
              <p className="m-0">{copy.handle.none}</p>
            ) : (
              <ol className="m-0 grid list-none gap-3 p-0">
                {reports.data.map((item, index) => (
                  <li
                    className="border border-border bg-card p-3"
                    key={`${index}-${item.updatedAt}`}
                  >
                    <StatusBlock
                      copy={copy}
                      format={format}
                      message={item.message}
                      next={item.nextAction}
                      status={item.status}
                      updatedAt={item.updatedAt}
                    />
                  </li>
                ))}
              </ol>
            )}
          </div>
        ) : null}
      </section>

      <p aria-live="polite" className={loading ? "m-0" : "sr-only"} role="status">
        {announcement}
      </p>
      <p className="m-0">
        <a className="font-semibold text-ledger-accent-strong underline" href={reportHref}>
          {copy.newReport}
        </a>
      </p>
    </div>
  );
}
