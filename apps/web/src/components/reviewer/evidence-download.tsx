"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { networkProblem, readBrowserProblem } from "@/lib/problems/browser-problem";
import { describeProblem, type SafeProblem } from "@/lib/problems/problem-messages";

type Phase = "idle" | "pending" | "done" | "failed";

/**
 * Downloads one cleaned evidence file only when asked. Each press makes a fresh authorised request
 * through the same-origin handler, so an expired session or link is a plain error and no address,
 * signed link, or file is ever stored: the bytes are held in memory just long enough to hand to the
 * browser's save dialog, then released. The file is never opened or previewed here.
 */
export function EvidenceDownload({
  copy,
  evidenceId,
  fileName,
  problems,
  reportId,
  signInHref,
  actions
}: Readonly<{
  actions: Messages["reviewer"]["actions"];
  copy: Messages["reviewer"]["download"];
  evidenceId: string;
  fileName: string;
  problems: Messages["problems"];
  reportId: string;
  signInHref: string;
}>): ReactNode {
  const [phase, setPhase] = useState<Phase>("idle");
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const controller = useRef<AbortController | undefined>(undefined);

  useEffect(
    () => () => {
      controller.current?.abort();
    },
    []
  );

  async function download(): Promise<void> {
    controller.current?.abort();
    controller.current = new AbortController();
    setPhase("pending");
    setProblem(undefined);

    try {
      const response = await fetch(
        `/api/reviewer/reports/${encodeURIComponent(reportId)}/evidence/${encodeURIComponent(evidenceId)}`,
        {
          method: "GET",
          cache: "no-store",
          credentials: "same-origin",
          signal: controller.current.signal
        }
      );

      if (!response.ok) {
        setProblem(await readBrowserProblem(response));
        setPhase("failed");
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = fileName;
      link.rel = "noopener";
      document.body.append(link);
      link.click();
      link.remove();
      // Released on the next task so the browser has already started the save.
      window.setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 0);
      setPhase("done");
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      setProblem(networkProblem());
      setPhase("failed");
    }
  }

  const view =
    problem === undefined ? undefined : describeProblem(problem, problems, formatMessageLite);
  const ended = problem?.status === 401;

  return (
    <div className="grid gap-2" data-slot="evidence-download">
      <div>
        <Button
          aria-disabled={phase === "pending"}
          aria-label={formatMessageLite(copy.buttonLabel, { name: fileName })}
          onClick={() => {
            if (phase !== "pending") {
              void download();
            }
          }}
          variant="secondary"
        >
          {phase === "pending" ? copy.pending : copy.button}
        </Button>
      </div>
      <div aria-live="polite" role="status">
        {phase === "done" ? (
          <small>{formatMessageLite(copy.done, { name: fileName })}</small>
        ) : null}
        {phase === "failed" && view !== undefined ? (
          <small className="grid gap-1 font-semibold text-destructive">
            <span>
              {copy.failed} {ended ? actions.sessionEnded : view.message}
            </span>
            {ended ? (
              <a className="underline" href={signInHref}>
                {actions.signIn}
              </a>
            ) : null}
            {view.referenceLine === undefined ? null : <span>{view.referenceLine}</span>}
          </small>
        ) : null}
      </div>
    </div>
  );
}
