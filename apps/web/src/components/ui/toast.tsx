"use client";

import type { ReactNode } from "react";

import { IconButton } from "@/components/ui/button";
import { Glyph } from "@/components/ui/feedback";
import { cn } from "@/lib/utils";

/** A transient message. Errors interrupt (`alert`); everything else waits its turn (`status`). */
export function Toast({
  children,
  dismissLabel,
  onDismiss,
  tone = "information"
}: Readonly<{
  children: ReactNode;
  dismissLabel: string;
  onDismiss: () => void;
  tone?: "information" | "danger";
}>): ReactNode {
  return (
    <div
      className={cn(
        "flex max-w-[68ch] items-start gap-3 rounded-ledger-control border border-border border-s-[0.375rem] bg-card p-3 [overflow-wrap:anywhere]",
        tone === "danger" ? "border-s-ledger-danger" : "border-s-ledger-information"
      )}
      data-slot="toast"
      role={tone === "danger" ? "alert" : "status"}
    >
      <Glyph>{tone === "danger" ? "×" : "i"}</Glyph>
      <div className="flex-1">{children}</div>
      <IconButton label={dismissLabel} onClick={onDismiss}>
        ×
      </IconButton>
    </div>
  );
}
