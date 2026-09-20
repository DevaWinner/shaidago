"use client";

import type { ReactNode } from "react";

import { RecoveryPage } from "./_components/recovery-page";
import { toSafeRequestReference } from "@/lib/support/request-reference";

type RecoverableError = Error & {
  requestId?: unknown;
};

type RouteErrorProperties = Readonly<{
  error: RecoverableError;
  reset: () => void;
}>;

export default function RouteError({ error, reset }: RouteErrorProperties): ReactNode {
  const reference = toSafeRequestReference(error.requestId);

  return (
    <RecoveryPage
      title="This page could not be loaded"
      reference={reference}
      action={
        <button type="button" onClick={reset}>
          Try again
        </button>
      }
    >
      Try again. If the problem continues, share the support reference without sharing private
      report details.
    </RecoveryPage>
  );
}
