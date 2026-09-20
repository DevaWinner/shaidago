"use client";

import type { ReactNode } from "react";

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
          title="ShaidaGo could not be opened"
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
      </body>
    </html>
  );
}
