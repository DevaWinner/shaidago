"use client";

import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import { Button, ButtonLink } from "@/components/ui/button";
import { Callout } from "@/components/ui/feedback";
import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import {
  clearReceipt,
  peekReceipt,
  subscribeToReceipt,
  type Receipt
} from "@/lib/report/receipt-store";

type Copy = Messages["report"];

const KNOWN_REASONS = [
  "unsupported_type",
  "spoofed_type",
  "active_content",
  "encrypted_pdf",
  "too_large",
  "too_many_pixels",
  "too_many_pages",
  "malformed",
  "malware_detected",
  "scan_failed",
  "storage_failed",
  "timeout"
] as const;

function reasonText(copy: Copy, reason: string | null): string {
  return (KNOWN_REASONS as readonly string[]).includes(reason ?? "")
    ? copy.complete.reasons[reason as (typeof KNOWN_REASONS)[number]]
    : copy.complete.reasons.malformed;
}

function Receipt_({
  copy,
  locale,
  receipt
}: Readonly<{ copy: Copy; locale: string; receipt: Receipt }>): ReactNode {
  const [copied, setCopied] = useState<"idle" | "done" | "failed">("idle");
  const text = copy.complete;

  async function copyCode(): Promise<void> {
    try {
      await navigator.clipboard.writeText(receipt.trackingCode);
      setCopied("done");
    } catch {
      setCopied("failed");
    }
  }

  function download(): void {
    const blob = new Blob([formatMessageLite(text.fileText, { code: receipt.trackingCode })], {
      type: "text/plain;charset=utf-8"
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "shaidago-tracking-code.txt";
    link.click();
    // The temporary address is dropped straight away; it never outlives the click.
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid gap-6">
      <p className="m-0 max-w-[68ch]">{text.lead}</p>
      <section
        aria-labelledby="code-heading"
        className="grid gap-3 border-2 border-foreground bg-card p-5"
      >
        <h2 className="m-0 text-ledger-lg" id="code-heading">
          {text.codeLabel}
        </h2>
        <p
          className="m-0 select-all font-mono text-ledger-xl font-bold tracking-wider [overflow-wrap:anywhere]"
          data-slot="tracking-code"
        >
          {receipt.trackingCode}
        </p>
        <Callout title={text.codeLabel} tone="warning">
          {text.codeWarning}
        </Callout>
        <div className="flex flex-wrap gap-3 print:hidden">
          <Button onClick={() => void copyCode()} variant="secondary">
            {text.copy}
          </Button>
          <Button onClick={() => window.print()} variant="secondary">
            {text.print}
          </Button>
          <Button onClick={download} variant="secondary">
            {text.download}
          </Button>
        </div>
        <p aria-live="polite" className="m-0 text-sm" role="status">
          {copied === "done" ? text.copied : copied === "failed" ? text.copyFailed : ""}
        </p>
      </section>

      <section aria-labelledby="next-heading" className="grid gap-2">
        <h2 className="m-0 text-ledger-lg" id="next-heading">
          {text.next.heading}
        </h2>
        <ul className="m-0 grid gap-1 pl-5">
          {receipt.nextSteps
            .filter((step): step is keyof Copy["complete"]["next"] =>
              ["save_tracking_code", "check_status_later", "see_escalation_guidance"].includes(step)
            )
            .map((step) => (
              <li key={step}>{text.next[step]}</li>
            ))}
        </ul>
        <p className="m-0">{receipt.contactSaved ? text.contactSaved : text.contactNotSaved}</p>
      </section>

      {receipt.attachments.length === 0 ? null : (
        <section aria-labelledby="files-heading" className="grid gap-2">
          <h2 className="m-0 text-ledger-lg" id="files-heading">
            {text.filesHeading}
          </h2>
          <ul className="m-0 grid gap-1 pl-5">
            {receipt.attachments.map((file) => (
              <li key={file.position}>
                {file.kept
                  ? formatMessageLite(text.fileKept, { number: file.position + 1 })
                  : formatMessageLite(text.fileRejected, {
                      number: file.position + 1,
                      reason: reasonText(copy, file.reason)
                    })}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="flex flex-wrap gap-3 print:hidden">
        <ButtonLink href={`/${locale}/track`} variant="secondary">
          {text.track}
        </ButtonLink>
        <ButtonLink href={`/${locale}`} onClick={() => clearReceipt()} variant="secondary">
          {text.leave}
        </ButtonLink>
      </div>
    </div>
  );
}

/**
 * Shows the tracking code only from the receipt this page's memory holds right now. It cannot be
 * reached from a URL, and a reload or a later visit finds nothing to show, and says so honestly
 * instead of showing a stale code. The receipt is dropped when the person leaves the page.
 */
export function Confirmation({
  copy,
  locale
}: Readonly<{ copy: Copy; locale: string }>): ReactNode {
  const receipt = useSyncExternalStore(subscribeToReceipt, peekReceipt, () => undefined);
  const pending = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    // A brief deferral survives React's development remount, which unmounts and mounts once.
    if (pending.current !== undefined) {
      clearTimeout(pending.current);
      pending.current = undefined;
    }

    return () => {
      pending.current = setTimeout(clearReceipt, 0);
    };
  }, []);

  if (receipt === undefined) {
    return (
      <div
        className="grid max-w-[68ch] gap-3 border border-border bg-card p-5"
        data-slot="receipt-lost"
      >
        <h1 className="m-0 text-ledger-xl">{copy.complete.lost.title}</h1>
        <p className="m-0">{copy.complete.lost.body}</p>
        <div>
          <ButtonLink href={`/${locale}/projects`} variant="secondary">
            {copy.complete.lost.newReport}
          </ButtonLink>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <h1 className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] leading-[1.1]">
        {copy.complete.title}
      </h1>
      <Receipt_ copy={copy} locale={locale} receipt={receipt} />
    </div>
  );
}
