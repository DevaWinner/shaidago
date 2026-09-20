"use client";

import {
  useEffect,
  useId,
  useState,
  useSyncExternalStore,
  type FormEvent,
  type ReactNode
} from "react";

import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { readBrowserProblem, networkProblem } from "@/lib/problems/browser-problem";
import { describeProblem, type SafeProblem } from "@/lib/problems/problem-messages";

type Copy = Messages["reviewer"]["signIn"];

function subscribeNever(): () => void {
  return () => undefined;
}

/**
 * Posts the credentials to the same-origin handler only. Nothing typed is written to storage, the
 * address, or a log; the password field is emptied after every attempt, and the handler answers
 * every failed attempt with the same generic message. On success the browser navigates to
 * `target`, which the server already reduced to an allowlisted reviewer route.
 */
export function SignInForm({
  copy,
  problems,
  required,
  target
}: Readonly<{
  copy: Copy;
  problems: Messages["problems"];
  required: string;
  target: string;
}>): ReactNode {
  const id = useId();
  const ready = useSyncExternalStore(
    subscribeNever,
    () => true,
    () => false
  );
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ identifier?: string; password?: string }>({});
  const [phase, setPhase] = useState<"idle" | "pending" | "done">("idle");
  const [problem, setProblem] = useState<SafeProblem | undefined>(undefined);
  const [waitUntil, setWaitUntil] = useState<number | undefined>(undefined);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (waitUntil === undefined) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, [waitUntil]);

  const remaining = waitUntil === undefined ? 0 : Math.max(0, Math.ceil((waitUntil - now) / 1000));
  const waiting = remaining > 0;

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (phase !== "idle" || waiting) {
      return;
    }

    const next = {
      ...(identifier.trim() === "" ? { identifier: copy.identifierRequired } : {}),
      ...(password === "" ? { password: copy.passwordRequired } : {})
    };

    setErrors(next);

    if (Object.keys(next).length > 0) {
      return;
    }

    setPhase("pending");
    setProblem(undefined);

    try {
      const response = await fetch("/api/reviewer/session", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier: identifier.trim(), password })
      });

      setPassword("");

      if (response.ok) {
        setPhase("done");
        window.location.assign(target);
        return;
      }

      const failure = await readBrowserProblem(response);

      setProblem(failure);
      setPhase("idle");

      if (failure.retryAfterSeconds !== undefined) {
        setNow(Date.now());
        setWaitUntil(Date.now() + failure.retryAfterSeconds * 1000);
      }
    } catch {
      setPassword("");
      setProblem(networkProblem());
      setPhase("idle");
    }
  }

  const view =
    problem === undefined ? undefined : describeProblem(problem, problems, formatMessageLite);
  const disabled = !ready || phase !== "idle" || waiting;

  return (
    <form
      className="grid max-w-[68ch] gap-4"
      data-slot="reviewer-sign-in"
      method="post"
      noValidate
      onSubmit={(event) => {
        void submit(event);
      }}
    >
      <Field
        controlId={`${id}-identifier`}
        error={errors.identifier}
        label={copy.identifier}
        required
        requiredLabel={required}
      >
        <Input
          autoCapitalize="none"
          autoComplete="username"
          autoCorrect="off"
          name="identifier"
          onChange={(event) => {
            setIdentifier(event.target.value);
          }}
          spellCheck={false}
          type="text"
          value={identifier}
        />
      </Field>
      <Field
        controlId={`${id}-password`}
        error={errors.password}
        label={copy.password}
        required
        requiredLabel={required}
      >
        <Input
          autoComplete="current-password"
          name="password"
          onChange={(event) => {
            setPassword(event.target.value);
          }}
          type="password"
          value={password}
        />
      </Field>
      <small className="text-muted-foreground">{copy.note}</small>
      <div>
        <Button aria-disabled={disabled} type="submit">
          {phase === "pending" ? copy.pending : copy.submit}
        </Button>
      </div>
      {view === undefined ? null : (
        <div
          className="grid gap-1 border-2 border-destructive bg-card p-4"
          data-slot="sign-in-failure"
          role="alert"
        >
          <strong>{copy.failureTitle}</strong>
          <p className="m-0">{view.message}</p>
          {waiting ? (
            <p className="m-0" data-slot="sign-in-wait">
              {formatMessageLite(copy.wait, { seconds: remaining })}
            </p>
          ) : view.retryHint === undefined ? null : (
            <p className="m-0">{copy.waitDone}</p>
          )}
          {view.mayHaveCompletedHint === undefined ? null : (
            <p className="m-0">{view.mayHaveCompletedHint}</p>
          )}
          {view.referenceLine === undefined ? null : (
            <p className="m-0 text-sm">{view.referenceLine}</p>
          )}
        </div>
      )}
    </form>
  );
}
