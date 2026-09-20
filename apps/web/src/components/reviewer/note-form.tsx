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

export const NOTE_MAX = 4000;

/**
 * Appends one private note. Notes cannot be edited or deleted, so sending needs an explicit second
 * confirmation. The text lives only in this component's memory; it is cleared after a success and
 * kept after a failure so nothing typed is lost to a retryable error. A dropped connection may
 * have saved the note, and the failure message says to check the list before sending again.
 */
export function NoteForm({
  actions,
  copy,
  locale,
  problems,
  reportId,
  signInHref
}: Readonly<{
  actions: Messages["reviewer"]["actions"];
  copy: Messages["reviewer"]["notes"];
  locale: string;
  problems: Messages["problems"];
  reportId: string;
  signInHref: string;
}>): ReactNode {
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

    if (text.trim() === "") {
      setError(copy.required);
      return;
    }
    if (text.length > NOTE_MAX) {
      setError(copy.tooLong);
      return;
    }

    setError(undefined);
    setOpen(true);
  }

  async function send(): Promise<void> {
    setPending(true);
    const outcome = await postJson(
      `/api/reviewer/reports/${encodeURIComponent(reportId)}/notes`,
      { body: text.trim() },
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
      data-slot="note-form"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        review();
      }}
    >
      <Field
        controlId={`${id}-note`}
        description={formatMessageLite(copy.hint, { max: NOTE_MAX })}
        error={error}
        label={copy.label}
      >
        <Textarea
          autoComplete="off"
          maxLength={NOTE_MAX + 200}
          onChange={(event) => {
            setText(event.target.value);
          }}
          rows={5}
          spellCheck
          value={text}
        />
      </Field>
      <small>{formatMessageLite(copy.counter, { count: text.length, max: NOTE_MAX })}</small>
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
