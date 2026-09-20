"use client";

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Callout, LiveRegion, StatusLabel } from "@/components/ui/feedback";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { networkProblem, readBrowserProblem } from "@/lib/problems/browser-problem";
import { describeProblem, type SafeProblem } from "@/lib/problems/problem-messages";
import { nextPollDelayMs, shouldPoll } from "@/lib/discovery/run-state";

type Copy = Readonly<{
  heading: string;
  intro: string;
  notice: string;
  start: string;
  stop: string;
  resume: string;
  checking: string;
  action: Record<"create" | "reuse_fresh" | "show_latest_completed", string>;
  states: Record<"queued" | "searching" | "analysing" | "needs_review" | "complete", string>;
  counts: string;
  replay: string;
  live: string;
  started: string;
  unavailable: string;
  invalid: string;
}>;

type Run = Readonly<{
  createdAt: string;
  demoReplay: boolean;
  progress: Readonly<{ analysed: number; fetched: number; resultsFound: number }>;
  runId: string;
  status: string;
  version: number;
}>;
type Phase =
  | Readonly<{ name: "idle" }>
  | Readonly<{ name: "starting" }>
  | Readonly<{ name: "viewing"; paused: boolean; run: Run }>
  | Readonly<{ name: "unavailable" }>
  | Readonly<{ name: "failed"; problem: SafeProblem }>;

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseRun(value: unknown): Run | undefined {
  if (!isRecord(value) || !isRecord(value["progress"])) return undefined;
  const progress = value["progress"];
  const count = (item: unknown): item is number =>
    typeof item === "number" && Number.isInteger(item) && item >= 0;

  if (
    typeof value["run_id"] !== "string" ||
    typeof value["status"] !== "string" ||
    typeof value["created_at"] !== "string" ||
    Number.isNaN(Date.parse(value["created_at"])) ||
    typeof value["demo_replay"] !== "boolean" ||
    !count(value["version"]) ||
    !count(progress["analysed"]) ||
    !count(progress["fetched"]) ||
    !count(progress["results_found"])
  ) {
    return undefined;
  }

  return {
    createdAt: value["created_at"],
    demoReplay: value["demo_replay"],
    progress: {
      analysed: progress["analysed"],
      fetched: progress["fetched"],
      resultsFound: progress["results_found"]
    },
    runId: value["run_id"],
    status: value["status"],
    version: value["version"]
  };
}

function parseStart(
  value: unknown
): Readonly<{ action: string; runId: string | null }> | undefined {
  if (!isRecord(value) || typeof value["action"] !== "string") return undefined;
  const runId = value["run_id"];

  return typeof runId === "string" || runId === null
    ? { action: value["action"], runId }
    : undefined;
}

const INVALID_RESPONSE: SafeProblem = {
  code: "internal_error",
  status: 200,
  requestId: undefined,
  retryAfterSeconds: undefined,
  fieldErrors: []
};

/** Public discovery stays in this island only: it is never placed in a route, cache, or storage. */
export function ProjectDiscovery({
  copy,
  locale,
  problems,
  slug
}: Readonly<{
  copy: Copy;
  locale: ApiLocale;
  problems: Parameters<typeof describeProblem>[1];
  slug: string;
}>): ReactNode {
  const headingId = useId();
  const [phase, setPhase] = useState<Phase>({ name: "idle" });
  const inFlight = useRef<AbortController | undefined>(undefined);
  const attempts = useRef(0);

  useEffect(() => () => inFlight.current?.abort(), []);

  const load = useCallback(
    async (runId: string): Promise<void> => {
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;
      const current = phase.name === "viewing" && phase.run.runId === runId ? phase.run : undefined;

      try {
        const params = current === undefined ? "" : `?since_version=${current.version}`;
        const response = await fetch(
          `/api/public/discovery/${encodeURIComponent(runId)}${params}`,
          {
            cache: "no-store",
            credentials: "same-origin",
            headers: { Accept: "application/json", "X-Shaidago-Locale": locale },
            signal: controller.signal
          }
        );
        if (response.status === 304) return;
        if (!response.ok) {
          setPhase({ name: "failed", problem: await readBrowserProblem(response) });
          return;
        }
        const run = parseRun(await response.json());
        setPhase(
          run === undefined
            ? { name: "failed", problem: INVALID_RESPONSE }
            : { name: "viewing", paused: false, run }
        );
      } catch (error) {
        if (!controller.signal.aborted) {
          setPhase({
            name: "failed",
            problem: error instanceof SyntaxError ? INVALID_RESPONSE : networkProblem()
          });
        }
      } finally {
        if (inFlight.current === controller) inFlight.current = undefined;
      }
    },
    [locale, phase]
  );

  async function start(): Promise<void> {
    if (inFlight.current !== undefined) return;
    const controller = new AbortController();
    inFlight.current = controller;
    attempts.current = 0;
    setPhase({ name: "starting" });
    try {
      const response = await fetch("/api/public/discovery", {
        body: JSON.stringify({ slug }),
        cache: "no-store",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-Shaidago-Locale": locale
        },
        method: "POST",
        signal: controller.signal
      });
      if (!response.ok) {
        setPhase({ name: "failed", problem: await readBrowserProblem(response) });
        return;
      }
      const result = parseStart(await response.json());
      if (result === undefined) {
        setPhase({ name: "failed", problem: INVALID_RESPONSE });
      } else if (result.runId === null || result.action === "unavailable") {
        setPhase({ name: "unavailable" });
      } else {
        await load(result.runId);
      }
    } catch {
      if (!controller.signal.aborted) setPhase({ name: "failed", problem: networkProblem() });
    } finally {
      if (inFlight.current === controller) inFlight.current = undefined;
    }
  }

  useEffect(() => {
    if (phase.name !== "viewing" || phase.paused || !shouldPoll("public", phase.run.status)) return;
    const runId = phase.run.runId;
    const poll = (): void => {
      if (!document.hidden && navigator.onLine) {
        attempts.current += 1;
        void load(runId);
      }
    };
    const timer = window.setTimeout(poll, nextPollDelayMs(attempts.current));
    return () => window.clearTimeout(timer);
  }, [load, phase]);

  const failure =
    phase.name === "failed" ? describeProblem(phase.problem, problems, (x) => x) : undefined;
  const active =
    phase.name === "starting" ||
    (phase.name === "viewing" && !phase.paused && shouldPoll("public", phase.run.status));
  const announcement =
    phase.name === "viewing"
      ? (copy.states[phase.run.status as keyof Copy["states"]] ?? copy.invalid)
      : active
        ? copy.checking
        : (failure?.message ?? "");

  return (
    <section
      aria-labelledby={headingId}
      className="grid max-w-[68ch] gap-4"
      data-slot="project-discovery"
    >
      <div className="grid gap-2 border-t border-border pt-8">
        <h2 className="m-0 text-ledger-xl leading-tight" id={headingId}>
          {copy.heading}
        </h2>
        <p className="m-0">{copy.intro}</p>
      </div>
      <Callout title={copy.notice} tone="information">
        <p className="m-0">{copy.intro}</p>
      </Callout>
      {phase.name === "viewing" ? (
        <div className="grid gap-3 border border-border bg-card p-4">
          <StatusLabel
            tone={
              phase.run.status === "complete"
                ? "reviewed"
                : phase.run.status === "failed"
                  ? "problem"
                  : "under-review"
            }
          >
            {copy.states[phase.run.status as keyof Copy["states"]] ?? copy.invalid}
          </StatusLabel>
          <p className="m-0 text-sm">
            {formatMessageLite(copy.counts, {
              analysed: phase.run.progress.analysed,
              fetched: phase.run.progress.fetched,
              found: phase.run.progress.resultsFound
            })}
          </p>
          <p className="m-0 text-sm text-muted-foreground">
            {phase.run.demoReplay ? copy.replay : copy.live}
          </p>
          <p className="m-0 text-sm text-muted-foreground">
            {copy.started}{" "}
            <time dateTime={phase.run.createdAt}>
              {new Intl.DateTimeFormat(locale, {
                dateStyle: "medium",
                timeStyle: "short",
                timeZone: "Africa/Lagos"
              }).format(new Date(phase.run.createdAt))}
            </time>
          </p>
          {shouldPoll("public", phase.run.status) ? (
            <div>
              <Button
                onClick={() => setPhase({ ...phase, paused: !phase.paused })}
                variant="secondary"
              >
                {phase.paused ? copy.resume : copy.stop}
              </Button>
            </div>
          ) : null}
        </div>
      ) : phase.name === "unavailable" ? (
        <Callout title={copy.unavailable} tone="warning">
          <p className="m-0">{copy.intro}</p>
        </Callout>
      ) : phase.name === "failed" ? (
        <Callout title={failure?.message ?? copy.invalid} tone="danger">
          <Button onClick={() => void start()} variant="secondary">
            {copy.start}
          </Button>
        </Callout>
      ) : (
        <Button disabled={active} onClick={() => void start()}>
          {copy.start}
        </Button>
      )}
      <LiveRegion>{announcement}</LiveRegion>
    </section>
  );
}
