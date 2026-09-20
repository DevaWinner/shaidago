"use client";

import { useId, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/utils";

type ChoiceProperties = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> &
  Readonly<{ label: string; description?: string }>;

const boxClasses = "m-0 size-6 flex-none accent-primary";
// The knob moves from start to end when on, so state is position as well as fill colour.
const switchClasses =
  "m-0 h-6 w-12 flex-none appearance-none rounded-lg border-2 border-foreground bg-[linear-gradient(var(--color-text),var(--color-text)),linear-gradient(var(--color-surface),var(--color-surface))] bg-[length:0.8rem_0.8rem,100%_100%] bg-[position:0.2rem_50%,0_0] bg-no-repeat checked:border-ledger-accent-strong checked:bg-[linear-gradient(var(--color-on-accent),var(--color-on-accent)),linear-gradient(var(--color-accent),var(--color-accent))] checked:bg-[position:calc(100%-0.2rem)_50%,0_0]";

function Choice({
  className,
  description,
  kind,
  label,
  ...properties
}: ChoiceProperties & Readonly<{ kind: "checkbox" | "radio" | "switch" }>): ReactNode {
  const id = useId();
  const descriptionId = description === undefined ? undefined : `${id}-description`;

  // The whole row is the label, so the touch target is the row, not the 24px control.
  return (
    <label
      className={cn("flex min-h-11 cursor-pointer items-start gap-3 py-2", className)}
      data-slot="choice"
      htmlFor={id}
    >
      <input
        aria-describedby={descriptionId}
        className={kind === "switch" ? switchClasses : boxClasses}
        id={id}
        role={kind === "switch" ? "switch" : undefined}
        type={kind === "radio" ? "radio" : "checkbox"}
        {...properties}
      />
      <span className="grid gap-1 [overflow-wrap:anywhere]">
        {label}
        {description === undefined ? null : (
          <small className="text-muted-foreground" id={descriptionId}>
            {description}
          </small>
        )}
      </span>
    </label>
  );
}

export function Checkbox(properties: ChoiceProperties): ReactNode {
  return <Choice kind="checkbox" {...properties} />;
}
export function Radio(properties: ChoiceProperties): ReactNode {
  return <Choice kind="radio" {...properties} />;
}
export function Switch(properties: ChoiceProperties): ReactNode {
  return <Choice kind="switch" {...properties} />;
}
