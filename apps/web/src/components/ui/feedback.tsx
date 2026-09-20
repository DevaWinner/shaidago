import { cva } from "class-variance-authority";
import {
  CircleAlert,
  CircleCheck,
  CircleHelp,
  CircleMinus,
  CircleX,
  Clock3,
  Info,
  TriangleAlert,
  type LucideIcon
} from "lucide-react";
import { useId, type ReactNode } from "react";

import { cn } from "@/lib/utils";

/** A decorative shape that accompanies words so a state is never colour alone. */
export function Glyph({
  children,
  className
}: Readonly<{ children: ReactNode; className?: string }>): ReactNode {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-grid size-5 min-w-5 flex-none place-items-center rounded-lg border-2 border-current px-1 text-xs leading-none font-extrabold",
        className
      )}
      data-slot="glyph"
    >
      {children}
    </span>
  );
}

const TONE_GLYPHS: Readonly<Record<"information" | "warning" | "danger", LucideIcon>> = {
  information: Info,
  warning: TriangleAlert,
  danger: CircleX
};
export type NoticeTone = keyof typeof TONE_GLYPHS;

const calloutVariants = cva(
  "grid gap-2 rounded-ledger-control border border-border border-s-[0.375rem] bg-card px-4 py-3 [overflow-wrap:anywhere]",
  {
    variants: {
      tone: {
        information: "border-s-ledger-information",
        warning: "border-s-ledger-warning",
        danger: "border-s-ledger-danger"
      }
    }
  }
);

export function Callout({
  children,
  title,
  tone = "information"
}: Readonly<{ children: ReactNode; title: string; tone?: NoticeTone }>): ReactNode {
  const ToneIcon = TONE_GLYPHS[tone];

  return (
    <div className={calloutVariants({ tone })} data-slot="callout" data-tone={tone} role="note">
      <strong className="flex items-start gap-2">
        <Glyph>
          <ToneIcon className="size-3.5" strokeWidth={2} />
        </Glyph>
        {title}
      </strong>
      <div>{children}</div>
    </div>
  );
}

export type StatusTone =
  "reviewed" | "under-review" | "limited-evidence" | "unavailable" | "problem";

const STATUS_GLYPHS: Readonly<Record<StatusTone, LucideIcon>> = {
  reviewed: CircleCheck,
  "under-review": Clock3,
  "limited-evidence": CircleHelp,
  unavailable: CircleMinus,
  problem: CircleAlert
};

const statusVariants = cva(
  "inline-flex items-start gap-2 rounded-lg border bg-card px-2 py-1 text-sm font-bold [overflow-wrap:anywhere]",
  {
    variants: {
      tone: {
        reviewed: "border-ledger-success",
        "under-review": "border-ledger-warning",
        "limited-evidence": "border-ledger-information",
        unavailable: "border-ledger-muted",
        problem: "border-ledger-danger"
      }
    }
  }
);

/** Status is always the words plus a shape; the border colour is reinforcement only. */
export function StatusLabel({
  children,
  className,
  tone = "reviewed"
}: Readonly<{ children: ReactNode; className?: string; tone?: StatusTone }>): ReactNode {
  const StatusIcon = STATUS_GLYPHS[tone];

  return (
    <span
      className={cn(statusVariants({ tone }), className)}
      data-slot="status-label"
      data-tone={tone}
    >
      <Glyph>
        <StatusIcon className="size-3.5" strokeWidth={2} />
      </Glyph>
      {children}
    </span>
  );
}

export function Disclosure({
  children,
  summary
}: Readonly<{ children: ReactNode; summary: string }>): ReactNode {
  return (
    <details className="border-y border-border py-3" data-slot="disclosure">
      <summary className="min-h-11 cursor-pointer py-2 font-bold">{summary}</summary>
      {children}
    </details>
  );
}

export function Progress({
  label,
  max = 100,
  value,
  valueText
}: Readonly<{ label: string; max?: number; value: number; valueText: string }>): ReactNode {
  const id = useId();

  return (
    <div className="grid gap-1" data-slot="progress">
      <label htmlFor={id}>{label}</label>
      <progress
        aria-valuetext={valueText}
        className="h-4 w-full appearance-none border border-border bg-card text-primary [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:bg-card [&::-webkit-progress-value]:bg-primary"
        id={id}
        max={max}
        value={value}
      />
      <span>{valueText}</span>
    </div>
  );
}

/** A named loading placeholder: stable rules and text, never an animated shimmer. */
export function Skeleton({ label }: Readonly<{ label: string }>): ReactNode {
  return (
    <div
      aria-live="polite"
      className="grid gap-2 text-muted-foreground"
      data-slot="skeleton"
      role="status"
    >
      <span aria-hidden="true" className="block h-3 border-y border-border bg-border" />
      <span>{label}</span>
    </div>
  );
}

export function LiveRegion({
  children,
  politeness = "polite"
}: Readonly<{ children: ReactNode; politeness?: "polite" | "assertive" }>): ReactNode {
  return (
    <div
      aria-atomic="true"
      aria-live={politeness}
      className="sr-only"
      role={politeness === "assertive" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}
