"use client";

import { Dialog } from "@base-ui/react/dialog";
import { Popover } from "@base-ui/react/popover";
import {
  createContext,
  useContext,
  useId,
  type AnchorHTMLAttributes,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes
} from "react";

/**
 * Project-owned primitives. They carry no product copy: every visible or spoken string arrives as
 * a prop so the four public locales can supply reviewed text (no English default can leak into
 * Hausa, Igbo, or Yoruba). They express semantics and state only; they decide nothing about
 * evidence, status, or authorisation.
 */

type ChildrenProperties = Readonly<{ children: ReactNode }>;

function joinClassNames(...names: readonly (string | false | undefined)[]): string {
  return names.filter((name): name is string => typeof name === "string" && name !== "").join(" ");
}

// ---------------------------------------------------------------------------------------------
// Actions

type ButtonVariant = "primary" | "secondary" | "danger";

export function Button({
  children,
  className,
  variant = "primary",
  ...properties
}: ButtonHTMLAttributes<HTMLButtonElement> & Readonly<{ variant?: ButtonVariant }>): ReactNode {
  return (
    <button
      className={joinClassNames("primitive-button", `primitive-button--${variant}`, className)}
      type="button"
      {...properties}
    >
      {children}
    </button>
  );
}

export function IconButton({
  children,
  className,
  label,
  ...properties
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label"> &
  Readonly<{ label: string }>): ReactNode {
  return (
    <Button
      aria-label={label}
      className={joinClassNames("primitive-icon-button", className)}
      variant="secondary"
      {...properties}
    >
      <span aria-hidden="true">{children}</span>
    </Button>
  );
}

export function Link({
  children,
  className,
  ...properties
}: Readonly<ChildrenProperties & AnchorHTMLAttributes<HTMLAnchorElement>>): ReactNode {
  return (
    <a className={joinClassNames("primitive-link", className)} {...properties}>
      {children}
    </a>
  );
}

// ---------------------------------------------------------------------------------------------
// Form fields: the label, description, and error are wired to the control automatically.

type FieldState = Readonly<{
  controlId: string;
  describedBy: string | undefined;
  invalid: boolean;
  required: boolean;
}>;

const FieldContext = createContext<FieldState | undefined>(undefined);

function useFieldControl<T extends { id?: string | undefined }>(
  properties: T & {
    "aria-describedby"?: string | undefined;
    "aria-invalid"?: boolean | "true" | "false" | "grammar" | "spelling" | undefined;
    required?: boolean | undefined;
  }
): T & {
  "aria-describedby": string | undefined;
  "aria-invalid": boolean | "true" | "false" | "grammar" | "spelling" | undefined;
  id: string | undefined;
  required: boolean | undefined;
} {
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
}: ChildrenProperties &
  Readonly<{
    controlId: string;
    description?: string;
    error?: string;
    label: string;
    required?: boolean;
    /** Localised text such as "required"; shown next to the label so it is not colour-only. */
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
      <div className="primitive-field">
        <label htmlFor={controlId}>
          {label}
          {required && requiredLabel !== undefined ? (
            <>
              {" "}
              <span className="primitive-required">({requiredLabel})</span>
            </>
          ) : null}
        </label>
        {children}
        {description === undefined ? null : (
          <small id={descriptionId} className="primitive-field-description">
            {description}
          </small>
        )}
        {error === undefined ? null : (
          <small id={errorId} className="primitive-field-error" role="alert">
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
      className={joinClassNames("primitive-input", className)}
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
      className={joinClassNames("primitive-input", className)}
      {...useFieldControl(properties)}
    />
  );
}

export function Select({
  children,
  className,
  ...properties
}: Readonly<ChildrenProperties & SelectHTMLAttributes<HTMLSelectElement>>): ReactNode {
  return (
    <select
      className={joinClassNames("primitive-input", className)}
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
}: Readonly<InputHTMLAttributes<HTMLInputElement> & { options: readonly string[] }>): ReactNode {
  const listId = useId();

  return (
    <>
      <input
        className={joinClassNames("primitive-input", className)}
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

type ChoiceProperties = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> &
  Readonly<{ label: string; description?: string }>;

function Choice({
  className,
  description,
  kind,
  label,
  ...properties
}: ChoiceProperties & Readonly<{ kind: "checkbox" | "radio" | "switch" }>): ReactNode {
  const id = useId();
  const descriptionId = description === undefined ? undefined : `${id}-description`;

  // The whole row is the label, so the touch target is the row, not the 20px control.
  return (
    <label className={joinClassNames("primitive-choice", className)} htmlFor={id}>
      <input
        aria-describedby={descriptionId}
        className={kind === "switch" ? "primitive-switch" : "primitive-check"}
        id={id}
        role={kind === "switch" ? "switch" : undefined}
        type={kind === "radio" ? "radio" : "checkbox"}
        {...properties}
      />
      <span className="primitive-choice-text">
        {label}
        {description === undefined ? null : (
          <small className="primitive-field-description" id={descriptionId}>
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

export function FilePicker({
  className,
  ...properties
}: Omit<InputHTMLAttributes<HTMLInputElement>, "type">): ReactNode {
  return (
    <input
      className={joinClassNames("primitive-file", className)}
      type="file"
      {...useFieldControl(properties)}
    />
  );
}

// ---------------------------------------------------------------------------------------------
// Disclosure, progress, loading, and notices

export function Disclosure({
  children,
  summary
}: Readonly<ChildrenProperties & { summary: string }>): ReactNode {
  return (
    <details className="primitive-disclosure">
      <summary>{summary}</summary>
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
    <div className="primitive-progress">
      <label htmlFor={id}>{label}</label>
      <progress aria-valuetext={valueText} id={id} max={max} value={value} />
      <span>{valueText}</span>
    </div>
  );
}

/** A named loading placeholder: stable rules and text, never an animated shimmer. */
export function Skeleton({ label }: Readonly<{ label: string }>): ReactNode {
  return (
    <div aria-live="polite" className="primitive-skeleton" role="status">
      <span className="primitive-skeleton-rule" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

const TONE_GLYPHS = {
  information: "i",
  warning: "!",
  danger: "×"
} as const;

export function Callout({
  children,
  title,
  tone = "information"
}: Readonly<ChildrenProperties & { title: string; tone?: keyof typeof TONE_GLYPHS }>): ReactNode {
  return (
    <div className={`primitive-callout primitive-callout--${tone}`} role="note">
      <strong className="primitive-callout-title">
        <span aria-hidden="true" className="primitive-glyph">
          {TONE_GLYPHS[tone]}
        </span>
        {title}
      </strong>
      <div>{children}</div>
    </div>
  );
}

const STATUS_GLYPHS = {
  reviewed: "✓",
  "under-review": "…",
  "limited-evidence": "△",
  unavailable: "–",
  problem: "!"
} as const;

/** Status is always the words plus a shape; the border colour is reinforcement only. */
export function StatusLabel({
  children,
  tone = "reviewed"
}: Readonly<ChildrenProperties & { tone?: keyof typeof STATUS_GLYPHS }>): ReactNode {
  return (
    <span className={`primitive-status primitive-status--${tone}`}>
      <span aria-hidden="true" className="primitive-glyph">
        {STATUS_GLYPHS[tone]}
      </span>
      {children}
    </span>
  );
}

/**
 * Cursor lists have no page count, so this offers previous/next links only. The URL owns the
 * state, which keeps filters shareable and the control usable without JavaScript.
 */
export function Pagination({
  label,
  next,
  previous
}: Readonly<{
  label: string;
  next?: Readonly<{ href: string; label: string }>;
  previous?: Readonly<{ href: string; label: string }>;
}>): ReactNode {
  return (
    <nav aria-label={label} className="primitive-pagination">
      {previous === undefined ? null : (
        <a className="primitive-button primitive-button--secondary" href={previous.href} rel="prev">
          {previous.label}
        </a>
      )}
      {next === undefined ? null : (
        <a className="primitive-button primitive-button--secondary" href={next.href} rel="next">
          {next.label}
        </a>
      )}
    </nav>
  );
}

// ---------------------------------------------------------------------------------------------
// Live regions and toast

export function LiveRegion({
  children,
  politeness = "polite"
}: ChildrenProperties & Readonly<{ politeness?: "polite" | "assertive" }>): ReactNode {
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

/** A transient message. Errors interrupt (`alert`); everything else waits its turn (`status`). */
export function Toast({
  children,
  dismissLabel,
  onDismiss,
  tone = "information"
}: ChildrenProperties &
  Readonly<{
    dismissLabel: string;
    onDismiss: () => void;
    tone?: "information" | "danger";
  }>): ReactNode {
  return (
    <div
      className={`primitive-toast primitive-toast--${tone}`}
      role={tone === "danger" ? "alert" : "status"}
    >
      <span aria-hidden="true" className="primitive-glyph">
        {TONE_GLYPHS[tone]}
      </span>
      <div>{children}</div>
      <IconButton label={dismissLabel} onClick={onDismiss}>
        ×
      </IconButton>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------
// Overlays. Each renders its own trigger so the library can restore focus to it on close.

type OverlayProperties = ChildrenProperties &
  Readonly<{
    closeLabel: string;
    description: string;
    onOpenChange?: (open: boolean) => void;
    open?: boolean;
    title: string;
    triggerLabel: string;
  }>;

function DialogShell({
  children,
  closeLabel,
  description,
  onOpenChange,
  open,
  placement,
  title,
  triggerLabel
}: OverlayProperties & Readonly<{ placement: "modal" | "sheet" }>): ReactNode {
  return (
    <Dialog.Root
      {...(onOpenChange === undefined ? {} : { onOpenChange })}
      {...(open === undefined ? {} : { open })}
    >
      <Dialog.Trigger className="primitive-button primitive-button--secondary">
        {triggerLabel}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className="primitive-backdrop" />
        <Dialog.Viewport className={`primitive-viewport primitive-viewport--${placement}`}>
          <Dialog.Popup className={`primitive-overlay primitive-overlay--${placement}`}>
            <Dialog.Title className="primitive-overlay-title">{title}</Dialog.Title>
            <Dialog.Description>{description}</Dialog.Description>
            {children}
            <Dialog.Close className="primitive-button primitive-button--secondary">
              {closeLabel}
            </Dialog.Close>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function Modal(properties: OverlayProperties): ReactNode {
  return <DialogShell {...properties} placement="modal" />;
}

/** The same dialog anchored to the bottom edge on small screens. */
export function Sheet(properties: OverlayProperties): ReactNode {
  return <DialogShell {...properties} placement="sheet" />;
}

/**
 * A decision that changes something needs an explicit second action. Cancel is first in focus
 * order and closing never confirms; `onConfirm` runs only from the confirm button.
 */
export function ConfirmDialog({
  cancelLabel,
  confirmLabel,
  description,
  destructive = false,
  onConfirm,
  title,
  triggerLabel
}: Readonly<{
  cancelLabel: string;
  confirmLabel: string;
  description: string;
  destructive?: boolean;
  onConfirm: () => void;
  title: string;
  triggerLabel: string;
}>): ReactNode {
  return (
    <Dialog.Root>
      <Dialog.Trigger className="primitive-button primitive-button--secondary">
        {triggerLabel}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Backdrop className="primitive-backdrop" />
        <Dialog.Viewport className="primitive-viewport primitive-viewport--modal">
          <Dialog.Popup className="primitive-overlay primitive-overlay--modal" role="alertdialog">
            <Dialog.Title className="primitive-overlay-title">{title}</Dialog.Title>
            <Dialog.Description>{description}</Dialog.Description>
            <div className="primitive-actions">
              <Dialog.Close className="primitive-button primitive-button--secondary">
                {cancelLabel}
              </Dialog.Close>
              <Dialog.Close
                className={`primitive-button primitive-button--${destructive ? "danger" : "primary"}`}
                onClick={onConfirm}
              >
                {confirmLabel}
              </Dialog.Close>
            </div>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function PopoverCard({
  children,
  content,
  triggerLabel
}: Readonly<{ children?: ReactNode; content: ReactNode; triggerLabel: string }>): ReactNode {
  return (
    <Popover.Root>
      <Popover.Trigger className="primitive-button primitive-button--secondary">
        {triggerLabel}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner>
          <Popover.Popup className="primitive-popover">{content}</Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
      {children}
    </Popover.Root>
  );
}
