"use client";

import type { ReactNode } from "react";

import { RECOVERY as recovery } from "@/lib/recovery-copy";
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
          title={recovery.fatal.title}
          referenceText={
            reference === undefined
              ? undefined
              : recovery.error.reference.replace("{reference}", reference)
          }
          action={
            <button type="button" onClick={reset}>
              {recovery.error.retry}
            </button>
          }
        >
          {recovery.error.body}
        </RecoveryPage>
      </body>
    </html>
  );
}
