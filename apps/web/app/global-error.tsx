"use client";

import type { ReactNode } from "react";

import en from "../messages/en.json";
import { RecoveryPage } from "./_components/recovery-page";
import { toSafeRequestReference } from "@/lib/support/request-reference";

type GlobalRecoverableError = Error & {
  requestId?: unknown;
};

type GlobalErrorProperties = Readonly<{
  error: GlobalRecoverableError;
  reset: () => void;
}>;

export default function GlobalError({ error, reset }: GlobalErrorProperties): ReactNode {
  const reference = toSafeRequestReference(error.requestId);

  return (
    <html lang="en">
      <body>
        <RecoveryPage
          title={en.recovery.error.title}
          referenceText={
            reference === undefined
              ? undefined
              : en.recovery.error.reference.replace("{reference}", reference)
          }
          action={
            <button type="button" onClick={reset}>
              {en.recovery.error.retry}
            </button>
          }
        >
          {en.recovery.error.body}
        </RecoveryPage>
      </body>
    </html>
  );
}
