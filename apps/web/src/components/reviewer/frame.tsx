import type { ReactNode } from "react";

import { TranslationNotice } from "@/components/evidence/evidence";
import { ReviewerShell } from "@/components/shell/shell";
import { SignOutButton } from "@/components/shell/sign-out-button";
import { resolveDomain } from "@/i18n/catalogue";
import type { ApiLocale } from "@/lib/api/forwarded-context";
import { queuePath, signInPath } from "@/lib/reviewer/safe-return";

/**
 * The frame every reviewer page shares. It is server-rendered, uses plain anchors (no prefetch of
 * private routes), and carries the language the reviewer copy is truly written in. Pages using it
 * must be dynamic and `no-store`; that is enforced by their route configuration and the e2e suite.
 */
export function ReviewerFrame({
  children,
  locale,
  signedIn
}: Readonly<{ children: ReactNode; locale: ApiLocale; signedIn: boolean }>): ReactNode {
  const shell = resolveDomain(locale, "shell");
  const reviewer = resolveDomain(locale, "reviewer");
  const evidence = resolveDomain(locale, "evidence");
  const problems = resolveDomain(locale, "problems");
  const copy = reviewer.messages;

  return (
    <ReviewerShell
      homeHref={`/${locale}`}
      messages={shell.messages.reviewer}
      queueHref={queuePath(locale)}
      sessionControl={
        signedIn ? (
          <SignOutButton
            failedMessage={problems.messages.codes.unavailable}
            label={copy.common.signOut}
            pendingLabel={copy.common.signingOut}
            signedOutHref={signInPath(locale, { reason: "signed_out" })}
          />
        ) : null
      }
    >
      <div className="grid gap-6" lang={reviewer.language}>
        {reviewer.isOriginal ? (
          <TranslationNotice labels={evidence.messages.translation} status="unavailable" />
        ) : null}
        <p
          className="m-0 border-2 border-double border-border p-3 text-sm"
          data-slot="private-banner"
        >
          <strong>{copy.common.noindex}.</strong> {copy.common.private}
        </p>
        {children}
      </div>
    </ReviewerShell>
  );
}
