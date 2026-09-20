"use client";

import { useRouter } from "next/navigation";
import { useId, useState, type ReactNode } from "react";

import { ActionFeedback } from "@/components/reviewer/action-feedback";
import { Button } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/field";
import { ConfirmDialog } from "@/components/ui/overlay";
import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { networkProblem } from "@/lib/problems/browser-problem";
import type { SafeProblem } from "@/lib/problems/problem-messages";
import { postJson } from "@/lib/tracking/client";

export const QUESTION_MIN = 5;
export const QUESTION_MAX = 500;

type Shared = Readonly<{
  actions: Messages["reviewer"]["actions"];
  copy: Messages["reviewer"]["questionActions"];
  locale: string;
  problems: Messages["problems"];
  reportId: string;
  signInHref: string;
}>;

/** Adds a reviewer question the reporter will see on the status page. It never changes the status. */
export function AskQuestionForm({
  actions,
  copy,
  locale,
  problems,
  reportId,
  signInHref
}: Shared): ReactNode {
  const id = useId();
  const router = useRouter();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const [added, setAdded] = useState(false);

  function review(): void {
    setAdded(false);
    setProblem(undefined);

    const length = text.trim().length;

    if (length < QUESTION_MIN) {
      setError(copy.tooShort);
      return;
    }
    if (length > QUESTION_MAX) {
      setError(copy.tooLong);
      return;
    }

    setError(undefined);
    setOpen(true);
  }

  async function send(): Promise<void> {
    setPending(true);
    const outcome = await postJson(
      `/api/reviewer/reports/${encodeURIComponent(reportId)}/follow-up-questions`,
      { question: text.trim() },
      { locale }
    );

    setPending(false);

    if (outcome.kind === "ok") {
      setText("");
      setAdded(true);
      router.refresh();
      return;
    }

    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
  }

  return (
    <form
      className="grid gap-3"
      data-slot="ask-question"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        review();
      }}
    >
      <Field controlId={`${id}-question`} description={copy.hint} error={error} label={copy.label}>
        <Textarea
          autoComplete="off"
          maxLength={QUESTION_MAX + 100}
          onChange={(event) => {
            setText(event.target.value);
          }}
          rows={3}
          value={text}
        />
      </Field>
      <small>{formatMessageLite(copy.counter, { count: text.length, max: QUESTION_MAX })}</small>
      <div>
        <Button aria-disabled={pending} type="submit">
          {pending ? actions.pending : copy.submit}
        </Button>
      </div>
      <ConfirmDialog
        cancelLabel={copy.cancel}
        confirmLabel={copy.confirm}
        description={copy.confirmBody}
        onConfirm={() => {
          void send();
        }}
        onOpenChange={setOpen}
        open={open}
        title={copy.confirmTitle}
      />
      <ActionFeedback
        actions={actions}
        problem={problem}
        problems={problems}
        signInHref={signInHref}
        success={added ? copy.added : undefined}
      />
    </form>
  );
}

/** Withdraws one question. The action needs confirmation because the reporter loses sight of it. */
export function WithdrawQuestionButton({
  actions,
  copy,
  locale,
  problems,
  question,
  questionId,
  reportId,
  signInHref
}: Shared & Readonly<{ question: string; questionId: string }>): ReactNode {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);

  async function withdraw(): Promise<void> {
    setPending(true);
    const outcome = await postJson(
      `/api/reviewer/reports/${encodeURIComponent(reportId)}/follow-up-questions/${encodeURIComponent(questionId)}/withdraw`,
      undefined,
      { locale }
    );

    setPending(false);

    if (outcome.kind === "ok") {
      router.refresh();
      return;
    }

    setProblem(outcome.kind === "problem" ? outcome.problem : networkProblem());
  }

  return (
    <div className="grid gap-2">
      <div>
        <Button
          aria-disabled={pending}
          aria-label={formatMessageLite(copy.withdrawLabel, { question })}
          onClick={() => {
            setProblem(undefined);
            setOpen(true);
          }}
          variant="secondary"
        >
          {pending ? actions.pending : copy.withdraw}
        </Button>
      </div>
      <ConfirmDialog
        cancelLabel={copy.cancel}
        confirmLabel={copy.withdrawConfirm}
        description={copy.withdrawBody}
        onConfirm={() => {
          void withdraw();
        }}
        onOpenChange={setOpen}
        open={open}
        title={copy.withdrawTitle}
      />
      <ActionFeedback
        actions={actions}
        problem={problem}
        problems={problems}
        signInHref={signInHref}
        success={undefined}
      />
    </div>
  );
}
