"use client";

import type { ReactNode } from "react";

import en from "../../messages/en.json";
import { RecoveryPage } from "../_components/recovery-page";
import { toSafeRequestReference } from "@/lib/support/request-reference";

type RecoverableError = Error & {
  requestId?: unknown;
};

type RouteErrorProperties = Readonly<{
  error: RecoverableError;
  reset: () => void;
}>;

const copy = en.recovery.error;

// Static English for now (the layout declares `lang="en"` for locales without reviewed copy).
export default function RouteError({ error, reset }: RouteErrorProperties): ReactNode {
  const reference = toSafeRequestReference(error.requestId);

  return (
    <RecoveryPage
      title={copy.title}
      // The catalogue's only variable here is `{reference}`; the parity check guarantees it exists.
      referenceText={
        reference === undefined ? undefined : copy.reference.replace("{reference}", reference)
      }
      action={
        <button type="button" onClick={reset}>
          {copy.retry}
        </button>
      }
    >
      {copy.body}
    </RecoveryPage>
  );
}
