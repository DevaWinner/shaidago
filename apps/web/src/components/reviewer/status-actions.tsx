"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition, type ReactNode } from "react";

import { ActionFeedback } from "@/components/reviewer/action-feedback";
import { Button } from "@/components/ui/button";
import { Field, Select, Textarea } from "@/components/ui/field";
import { ConfirmDialog } from "@/components/ui/overlay";
import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { networkProblem } from "@/lib/problems/browser-problem";
import type { SafeProblem } from "@/lib/problems/problem-messages";
import {
  CONSEQUENTIAL,
  NEEDS_MESSAGE,
  NEEDS_REASON,
  isReportStatus,
  transitionsFrom,
  type ReviewerCommand
} from "@/lib/reviewer/transitions";
import { postJson } from "@/lib/tracking/client";

export const MESSAGE_MAX = 400;
export const REASON_MAX = 1200;

type Labels = Messages["reviewer"]["queue"]["statuses"];
type Result = Readonly<{ from: string; to: string }>;

function label(table: Labels, status: string): string {
  return (table as Readonly<Record<string, string | undefined>>)[status] ?? status;
}

/**
 * Status controls. It offers only the commands the contract allows from the current status, sends
 * the status and version it was rendered with (so a stale view is refused, not overwritten), and
 * locks while a request is pending. FastAPI decides; a refusal (`409`) keeps what the reviewer
 * typed and offers a reload of the latest state. Nothing here publishes text: a transition's only
 * public effect is the reporter-visible status, and the success message says nothing was published.
 */
export function StatusActions({
  actions,
  copy,
  locale,
  problems,
  reportId,
  signInHref,
  statuses,
  status,
  version
}: Readonly<{
  actions: Messages["reviewer"]["actions"];
  copy: Messages["reviewer"]["transition"];
  locale: string;
  problems: Messages["problems"];
  reportId: string;
  signInHref: string;
  statuses: Labels;
  status: string;
  version: number;
}>): ReactNode {
  const id = useId();
  const router = useRouter();
  const [reloading, startReload] = useTransition();
  const options = transitionsFrom(status);
  const [command, setCommand] = useState<ReviewerCommand | "">(options[0]?.command ?? "");
  const [message, setMessage] = useState("");
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<{ message?: string; reason?: string }>({});
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const [result, setResult] = useState<Result | undefined>(undefined);

  const chosen = options.find((option) => option.command === command) ?? options[0];

  // A different status (after a reload) may not offer the chosen command any more.
  if (chosen !== undefined && chosen.command !== command) {
    setCommand(chosen.command);
  }

  if (chosen === undefined || !isReportStatus(status)) {
    return <p className="m-0">{copy.none}</p>;
  }

  function review(): void {
    if (chosen === undefined || pending) {
      return;
    }

    const next: { message?: string; reason?: string } = {};
    const trimmedMessage = message.trim();
    const trimmedReason = reason.trim();

    if (NEEDS_MESSAGE.has(chosen.command) && trimmedMessage === "") {
      next.message = copy.messageRequired;
    } else if (trimmedMessage.length > MESSAGE_MAX) {
      next.message = copy.messageTooLong;
    }
    if (NEEDS_REASON.has(chosen.command) && trimmedReason === "") {
      next.reason = copy.reasonRequired;
    } else if (trimmedReason.length > REASON_MAX) {
      next.reason = copy.reasonTooLong;
    }

    setErrors(next);
    setProblem(undefined);
    setResult(undefined);

    if (Object.keys(next).length === 0) {
      setOpen(true);
    }
  }

  async function send(): Promise<void> {
    if (chosen === undefined) {
      return;
    }

    const from = status;
    const to = chosen.to;

    setPending(true);
    const outcome = await postJson(
      `/api/reviewer/reports/${encodeURIComponent(reportId)}/status-transition`,
      {
        command: chosen.command,
        expected_status: status,
        expected_version: version,
        ...(reason.trim() === "" ? {} : { internal_reason: reason.trim() }),
        ...(message.trim() === "" ? {} : { reporter_message: message.trim() })
      },
      { locale }
    );

    setPending(false);

    if (outcome.kind === "ok") {
      setResult({ from, to });
      setMessage("");
      setReason("");
      router.refresh();
      return;
    }

    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
  }

  const conflict = problem?.status === 409;
  const careful = CONSEQUENTIAL.has(chosen.command);
  return (
    <form
      className="grid gap-4"
      data-slot="status-actions"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        review();
      }}
    >
      <fieldset className="m-0 grid gap-3 border-0 p-0" disabled={pending || reloading}>
        <legend className="mb-2 font-semibold">{copy.legend}</legend>
        <Field
          controlId={`${id}-command`}
          description={formatMessageLite(copy.commandHelp, {
            from: label(statuses, status),
            to: label(statuses, chosen.to)
          })}
          label={copy.command}
        >
          <Select
            onChange={(event) => {
              setCommand(event.target.value as ReviewerCommand);
              setErrors({});
            }}
            value={chosen.command}
          >
            {options.map((option) => (
              <option key={option.command} value={option.command}>
                {copy.commands[option.command]}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          controlId={`${id}-message`}
          description={formatMessageLite(copy.messageHint, { max: MESSAGE_MAX })}
          error={errors.message}
          label={copy.message}
          required={NEEDS_MESSAGE.has(chosen.command)}
        >
          <Textarea
            autoComplete="off"
            onChange={(event) => {
              setMessage(event.target.value);
            }}
            rows={3}
            value={message}
          />
        </Field>
        <small>
          {formatMessageLite(copy.counter, { count: message.length, max: MESSAGE_MAX })}
        </small>
        <Field
          controlId={`${id}-reason`}
          description={formatMessageLite(copy.reasonHint, { max: REASON_MAX })}
          error={errors.reason}
          label={copy.reason}
          required={NEEDS_REASON.has(chosen.command)}
        >
          <Textarea
            autoComplete="off"
            onChange={(event) => {
              setReason(event.target.value);
            }}
            rows={3}
            value={reason}
          />
        </Field>
        <div>
          <Button aria-disabled={pending} type="submit">
            {pending ? copy.pending : copy.submit}
          </Button>
        </div>
      </fieldset>
      <small className="text-muted-foreground">{copy.publishNote}</small>
      <ConfirmDialog
        cancelLabel={copy.cancel}
        confirmLabel={copy.confirm}
        description={careful ? `${copy.confirmBody} ${copy.confirmCareful}` : copy.confirmBody}
        onConfirm={() => {
          void send();
        }}
        onOpenChange={setOpen}
        open={open}
        title={formatMessageLite(copy.confirmTitle, { to: label(statuses, chosen.to) })}
      />
      {conflict ? (
        <div className="grid gap-2 border-2 border-destructive bg-card p-3" role="alert">
          <p className="m-0">{copy.conflict}</p>
          <div>
            <Button
              aria-disabled={reloading}
              onClick={() => {
                if (reloading) {
                  return;
                }

                setProblem(undefined);
                // A transition keeps the form locked until the fresh status and version arrive, so
                // the next attempt is made against the reloaded state, not the stale one.
                startReload(() => {
                  router.refresh();
                });
              }}
              variant="secondary"
            >
              {reloading ? copy.reloading : copy.reload}
            </Button>
          </div>
        </div>
      ) : (
        <ActionFeedback
          actions={actions}
          problem={problem}
          problems={problems}
          signInHref={signInHref}
          success={
            result === undefined
              ? undefined
              : formatMessageLite(copy.done, {
                  from: label(statuses, result.from),
                  to: label(statuses, result.to)
                })
          }
        />
      )}
    </form>
  );
}
