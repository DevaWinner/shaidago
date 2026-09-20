"use client";

import { useEffect, useId, useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Callout } from "@/components/ui/feedback";
import { Checkbox } from "@/components/ui/choice";
import { Field, Input } from "@/components/ui/field";
import type { Messages } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { describeProblem, type SafeProblem } from "@/lib/problems/problem-messages";
import { parseHandleCreated, postJson } from "@/lib/tracking/client";

type Copy = Messages["handle"];

type Created = Readonly<{ handle: string; passphrase: string }>;

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

/**
 * Handle creation and deletion. A new handle and passphrase exist only in this component's state:
 * they are shown once, never stored, never copied unless asked, and gone after a reload. There is no
 * recovery, and the wording never calls a handle an account, a sign-in, or proof of identity.
 * Deleting only unlinks reports, and says so before asking for confirmation.
 */
export function HandlePanel({
  copy,
  locale,
  problems,
  trackHref
}: Readonly<{
  copy: Copy;
  locale: ApiLocale;
  problems: Messages["problems"];
  trackHref: string;
}>): ReactNode {
  const id = useId();
  const ready = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false
  );
  const [created, setCreated] = useState<Created | undefined>(undefined);
  const [creating, setCreating] = useState(false);
  const [failure, setFailure] = useState<SafeProblem | undefined>(undefined);
  const [copied, setCopied] = useState<"idle" | "done" | "failed">("idle");
  const [handle, setHandle] = useState("");
  const [passphrase, setPassphrase] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [confirmError, setConfirmError] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [deleteFailure, setDeleteFailure] = useState<SafeProblem | undefined>(undefined);
  const createKey = useRef<string | undefined>(undefined);
  const result = useRef<HTMLHeadingElement>(null);
  const deleteResult = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (created !== undefined) {
      result.current?.focus();
    }
  }, [created]);
  useEffect(() => {
    if (deleted || deleteFailure !== undefined) {
      deleteResult.current?.focus();
    }
  }, [deleted, deleteFailure]);

  async function create(): Promise<void> {
    if (creating) {
      return;
    }
    setCreating(true);
    setFailure(undefined);
    // One key per creation attempt, reused if the answer was lost, so a retry cannot make two handles.
    createKey.current ??= crypto.randomUUID();

    const outcome = await postJson("/api/reporter-handle", undefined, {
      locale,
      idempotencyKey: createKey.current
    });

    setCreating(false);
    if (outcome.kind === "ok") {
      const parsed = parseHandleCreated(outcome.data);

      if (parsed === undefined) {
        setFailure(INVALID);
      } else {
        createKey.current = undefined;
        setCopied("idle");
        setCreated(parsed);
      }
    } else if (outcome.kind === "problem") {
      setFailure(outcome.problem);
    } else if (outcome.kind === "network") {
      setFailure({ ...INVALID, code: "network_unavailable", status: undefined });
    }
  }

  async function remove(): Promise<void> {
    if (deleting) {
      return;
    }
    if (!confirm) {
      setConfirmError(true);
      return;
    }
    setConfirmError(false);
    setDeleting(true);
    setDeleteFailure(undefined);

    const outcome = await postJson(
      "/api/reporter-handle/delete",
      { handle: handle.trim(), passphrase },
      { locale }
    );

    setDeleting(false);
    if (outcome.kind === "ok") {
      // Credentials are cleared as soon as the handle is gone.
      setHandle("");
      setPassphrase("");
      setConfirm(false);
      setDeleted(true);
    } else if (outcome.kind === "problem") {
      setDeleted(false);
      setDeleteFailure(outcome.problem);
    } else if (outcome.kind === "network") {
      setDeleteFailure({ ...INVALID, code: "network_unavailable", status: undefined });
    }
  }

  async function copyBoth(current: Created): Promise<void> {
    try {
      await navigator.clipboard.writeText(`${current.handle}\n${current.passphrase}`);
      setCopied("done");
    } catch {
      setCopied("failed");
    }
  }

  function download(current: Created): void {
    const url = URL.createObjectURL(
      new Blob([formatMessageLite(copy.created.fileText, current)], {
        type: "text/plain;charset=utf-8"
      })
    );
    const link = document.createElement("a");

    link.href = url;
    link.download = "shaidago-reporter-handle.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  const failureView =
    failure === undefined ? undefined : describeProblem(failure, problems, formatMessageLite);
  const deleteView =
    deleteFailure === undefined
      ? undefined
      : describeProblem(deleteFailure, problems, formatMessageLite);
  const section = "grid gap-4 border-t border-border pt-8";

  return (
    <div className="grid max-w-[68ch] gap-8" data-slot="handle-panel">
      <p className="m-0 text-sm text-muted-foreground" hidden={ready}>
        {copy.needsScript}
      </p>
      <section aria-labelledby={`${id}-facts`} className="grid gap-2">
        <h2 className="m-0 text-ledger-xl" id={`${id}-facts`}>
          {copy.facts.heading}
        </h2>
        <ul className="m-0 grid gap-1 pl-5">
          <li>{copy.facts.benefit}</li>
          <li>{copy.facts.risk}</li>
          <li>{copy.facts.recovery}</li>
        </ul>
      </section>

      <section aria-labelledby={`${id}-create`} className={section}>
        <h2 className="m-0 text-ledger-xl" id={`${id}-create`}>
          {copy.create.heading}
        </h2>
        <p className="m-0 text-sm text-muted-foreground">{copy.create.again}</p>
        {created === undefined ? (
          <div>
            <Button
              aria-disabled={creating || !ready}
              disabled={!ready}
              onClick={() => void create()}
            >
              {copy.create.button}
            </Button>
          </div>
        ) : (
          <div
            className="grid gap-3 border-2 border-foreground bg-card p-5"
            data-slot="handle-created"
          >
            <h3 className="m-0 text-ledger-lg" ref={result} tabIndex={-1}>
              {copy.created.heading}
            </h3>
            <dl className="m-0 grid gap-2">
              <div>
                <dt className="text-sm text-muted-foreground">{copy.created.handle}</dt>
                <dd
                  className="m-0 select-all font-mono text-ledger-lg font-bold [overflow-wrap:anywhere]"
                  data-slot="created-handle"
                >
                  {created.handle}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-muted-foreground">{copy.created.passphrase}</dt>
                <dd
                  className="m-0 select-all font-mono text-ledger-lg font-bold [overflow-wrap:anywhere]"
                  data-slot="created-passphrase"
                >
                  {created.passphrase}
                </dd>
              </div>
            </dl>
            <Callout title={copy.created.heading} tone="warning">
              {copy.created.warning}
            </Callout>
            <p className="m-0">{copy.created.use}</p>
            <div className="flex flex-wrap gap-3 print:hidden">
              <Button onClick={() => void copyBoth(created)} variant="secondary">
                {copy.created.copy}
              </Button>
              <Button onClick={() => window.print()} variant="secondary">
                {copy.created.print}
              </Button>
              <Button onClick={() => download(created)} variant="secondary">
                {copy.created.download}
              </Button>
              <Button
                onClick={() => {
                  setCreated(undefined);
                  setCopied("idle");
                }}
                variant="secondary"
              >
                {copy.created.done}
              </Button>
            </div>
            <p aria-live="polite" className="m-0 text-sm" role="status">
              {copied === "done"
                ? copy.created.copied
                : copied === "failed"
                  ? copy.created.copyFailed
                  : ""}
            </p>
          </div>
        )}
        {failureView === undefined ? null : (
          <div
            className="grid gap-2 border-2 border-destructive bg-card p-4"
            data-slot="handle-failure"
            role="alert"
          >
            <h3 className="m-0 text-ledger-lg">{copy.create.heading}</h3>
            <p className="m-0">{failureView.message}</p>
            {failureView.referenceLine === undefined ? null : (
              <p className="m-0 text-sm">{failureView.referenceLine}</p>
            )}
          </div>
        )}
      </section>

      <section aria-labelledby={`${id}-delete`} className={section}>
        <h2 className="m-0 text-ledger-xl" id={`${id}-delete`}>
          {copy.delete.heading}
        </h2>
        <p className="m-0 max-w-[68ch]">{copy.delete.explain}</p>
        <form
          className="grid gap-3"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            void remove();
          }}
        >
          <Field controlId={`${id}-h`} label={copy.delete.handleLabel}>
            <Input
              autoCapitalize="off"
              autoComplete="off"
              maxLength={64}
              onChange={(event) => setHandle(event.target.value)}
              spellCheck={false}
              value={handle}
            />
          </Field>
          <Field controlId={`${id}-p`} label={copy.delete.passphraseLabel}>
            <Input
              autoCapitalize="off"
              autoComplete="off"
              maxLength={200}
              onChange={(event) => setPassphrase(event.target.value)}
              spellCheck={false}
              type="password"
              value={passphrase}
            />
          </Field>
          <Checkbox
            checked={confirm}
            label={copy.delete.confirm}
            onChange={(event) => {
              setConfirm(event.target.checked);
              setConfirmError(false);
            }}
          />
          {confirmError ? (
            <p className="m-0 font-semibold text-destructive" role="alert">
              {copy.delete.needConfirm}
            </p>
          ) : null}
          <div>
            <Button aria-disabled={deleting || !ready} disabled={!ready} type="submit">
              {copy.delete.submit}
            </Button>
          </div>
        </form>
        {deleted || deleteView !== undefined ? (
          <div
            className="grid gap-2 border border-border bg-card p-4"
            data-slot="delete-result"
            ref={deleteResult}
            tabIndex={-1}
          >
            {deleted ? (
              <p className="m-0 font-semibold">{copy.delete.done}</p>
            ) : (
              <>
                <h3 className="m-0 text-ledger-lg">{copy.delete.failedTitle}</h3>
                <p className="m-0">{deleteView?.message}</p>
              </>
            )}
          </div>
        ) : null}
      </section>

      <p className="m-0">
        <a className="font-semibold text-ledger-accent-strong underline" href={trackHref}>
          {copy.statusLink}
        </a>
      </p>
    </div>
  );
}
