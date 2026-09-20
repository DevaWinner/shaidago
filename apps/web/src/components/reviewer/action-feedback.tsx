"use client";

import type { ReactNode } from "react";

import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { describeProblem, type SafeProblem } from "@/lib/problems/problem-messages";

/**
 * The outcome of a reviewer mutation, always in words. A `401` is an ended session and offers
 * sign-in; every other failure uses the reviewed message for its stable code, never backend text.
 * `role="alert"` is used for failures and `role="status"` for success so each is announced once.
 */
export function ActionFeedback({
  actions,
  problem,
  problems,
  signInHref,
  success
}: Readonly<{
  actions: Messages["reviewer"]["actions"];
  problem: SafeProblem | undefined;
  problems: Messages["problems"];
  signInHref: string;
  success: string | undefined;
}>): ReactNode {
  if (problem === undefined) {
    return (
      <div role="status">
        {success === undefined ? null : <p className="m-0 font-semibold">{success}</p>}
      </div>
    );
  }

  const view = describeProblem(problem, problems, formatMessageLite, { mutation: true });
  const ended = problem.status === 401;

  return (
    <div className="grid gap-1 border-2 border-destructive bg-card p-3" role="alert">
      <p className="m-0">{ended ? actions.sessionEnded : view.message}</p>
      {ended ? (
        <p className="m-0">
          <a className="font-semibold underline" href={signInHref}>
            {actions.signIn}
          </a>
        </p>
      ) : null}
      {view.retryHint === undefined ? null : <p className="m-0">{view.retryHint}</p>}
      {view.mayHaveCompletedHint === undefined ? null : (
        <p className="m-0">{view.mayHaveCompletedHint}</p>
      )}
      {view.referenceLine === undefined ? null : (
        <p className="m-0 text-sm">{view.referenceLine}</p>
      )}
    </div>
  );
}
