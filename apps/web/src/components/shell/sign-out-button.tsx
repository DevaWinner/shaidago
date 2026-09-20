"use client";

import { useState, type ReactNode } from "react";

import { Button } from "@/components/primitives/primitives";

/**
 * Signs out through the same-origin handler, which always clears the cookies. It sends no token:
 * the session and CSRF values are HttpOnly and travel only as cookies. A failure is stated, because
 * an unreachable API may not have revoked the server-side session.
 */
export function SignOutButton({
  failedMessage,
  label,
  pendingLabel,
  signedOutHref
}: Readonly<{
  failedMessage: string;
  label: string;
  pendingLabel: string;
  signedOutHref: string;
}>): ReactNode {
  const [state, setState] = useState<"idle" | "pending" | "failed">("idle");

  async function signOut(): Promise<void> {
    setState("pending");

    try {
      const response = await fetch("/api/reviewer/session", {
        method: "DELETE",
        credentials: "same-origin"
      });

      if (!response.ok) {
        setState("failed");
        return;
      }

      window.location.assign(signedOutHref);
    } catch {
      setState("failed");
    }
  }

  return (
    <div className="ms-auto grid gap-1">
      <Button
        aria-disabled={state === "pending"}
        onClick={() => {
          if (state !== "pending") {
            void signOut();
          }
        }}
        variant="secondary"
      >
        {state === "pending" ? pendingLabel : label}
      </Button>
      {state === "failed" ? (
        <p className="font-semibold text-destructive" role="alert">
          {failedMessage}
        </p>
      ) : null}
    </div>
  );
}
