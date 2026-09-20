"use client";

import {
  createContext,
  useContext,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes
} from "react";

import { cn } from "@/lib/utils";

type FieldState = Readonly<{
  controlId: string;
  describedBy: string | undefined;
  invalid: boolean;
  required: boolean;
}>;

const FieldContext = createContext<FieldState | undefined>(undefined);

const controlClasses =
  "box-border min-h-11 w-full min-w-0 max-w-full rounded-ledger-control border border-border bg-card px-3 py-2 text-foreground [overflow-wrap:anywhere] read-only:border-dashed read-only:bg-[var(--state-read-only-background)] read-only:text-[var(--state-read-only-text)] aria-invalid:border-2 aria-invalid:border-destructive";

type ControlProperties = {
  id?: string | undefined;
  "aria-describedby"?: string | undefined;
  "aria-invalid"?: boolean | "true" | "false" | "grammar" | "spelling" | undefined;
  required?: boolean | undefined;
};

/** Merges the surrounding Field's id, description, error, and required state into a control. */
function useFieldControl<T extends ControlProperties>(properties: T): T {
  const field = useContext(FieldContext);
  const describedBy = [properties["aria-describedby"], field?.describedBy]
    .filter((part): part is string => part !== undefined && part !== "")
    .join(" ");

  return {
    ...properties,
    id: properties.id ?? field?.controlId,
    "aria-describedby": describedBy === "" ? undefined : describedBy,
    "aria-invalid": properties["aria-invalid"] ?? (field?.invalid === true ? true : undefined),
    required: properties.required ?? (field?.required === true ? true : undefined)
  };
}

export function Field({
  children,
  controlId,
  description,
  error,
  label,
  required = false,
  requiredLabel
}: Readonly<{
  children: ReactNode;
  controlId: string;
  description?: string;
  error?: string;
  label: string;
  required?: boolean;
  /** Localised text such as "required"; shown beside the label so it is not colour-only. */
  requiredLabel?: string;
}>): ReactNode {
  const descriptionId = description === undefined ? undefined : `${controlId}-description`;
  const errorId = error === undefined ? undefined : `${controlId}-error`;
  const describedBy = [descriptionId, errorId].filter(Boolean).join(" ");

  return (
    <FieldContext.Provider
      value={{
        controlId,
        describedBy: describedBy === "" ? undefined : describedBy,
        invalid: error !== undefined,
        required
      }}
    >
      <div className="grid max-w-[68ch] grid-cols-[minmax(0,1fr)] gap-1" data-slot="field">
        <label className="font-semibold [overflow-wrap:anywhere]" htmlFor={controlId}>
          {label}
          {required && requiredLabel !== undefined ? (
            <>
              {" "}
              <span>({requiredLabel})</span>
            </>
          ) : null}
        </label>
        {children}
        {description === undefined ? null : (
          <small className="text-muted-foreground [overflow-wrap:anywhere]" id={descriptionId}>
            {description}
          </small>
        )}
        {error === undefined ? null : (
          <small
            className="font-semibold text-destructive [overflow-wrap:anywhere]"
            id={errorId}
            role="alert"
          >
            {error}
          </small>
        )}
      </div>
    </FieldContext.Provider>
  );
}

export function Input({
  className,
  ...properties
}: InputHTMLAttributes<HTMLInputElement>): ReactNode {
  return (
    <input
      className={cn(controlClasses, className)}
      data-slot="input"
      {...useFieldControl(properties)}
    />
  );
}

export function Textarea({
  className,
  ...properties
}: TextareaHTMLAttributes<HTMLTextAreaElement>): ReactNode {
  return (
    <textarea
      className={cn(controlClasses, className)}
      data-slot="input"
      {...useFieldControl(properties)}
    />
  );
}

/** WebKit ignores min-height on a natively drawn select, so the chevron is drawn from tokens. */
export function Select({
  children,
  className,
  ...properties
}: SelectHTMLAttributes<HTMLSelectElement>): ReactNode {
  return (
    <select
      className={cn(
        controlClasses,
        "appearance-none truncate pe-8 bg-[linear-gradient(45deg,transparent_50%,var(--color-text)_50%),linear-gradient(135deg,var(--color-text)_50%,transparent_50%)] bg-[length:0.4rem_0.4rem,0.4rem_0.4rem] bg-[position:calc(100%-1.25rem)_50%,calc(100%-0.9rem)_50%] bg-no-repeat",
        className
      )}
      data-slot="input"
      {...useFieldControl(properties)}
    >
      {children}
    </select>
  );
}

/** A native input with a suggestion list: real combobox semantics without a script dependency. */
export function Combobox({
  className,
  options,
  ...properties
}: InputHTMLAttributes<HTMLInputElement> & Readonly<{ options: readonly string[] }>): ReactNode {
  const listId = useId();

  return (
    <>
      <input
        className={cn(controlClasses, className)}
        data-slot="input"
        list={listId}
        {...useFieldControl(properties)}
      />
      <datalist id={listId}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </>
  );
}

export function FilePicker({
  className,
  ...properties
}: Omit<InputHTMLAttributes<HTMLInputElement>, "type">): ReactNode {
  return (
    <input
      className={cn(controlClasses, className)}
      data-slot="input"
      type="file"
      {...useFieldControl(properties)}
    />
  );
}
