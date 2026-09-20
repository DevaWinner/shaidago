"use client";

import { Dialog } from "@base-ui/react/dialog";
import { Popover } from "@base-ui/react/popover";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes
} from "react";

type ChildrenProperties = Readonly<{ children: ReactNode }>;
type FieldProperties = Readonly<
  ChildrenProperties & { controlId: string; description?: string; error?: string; label: string }
>;

export function Button({
  children,
  className = "",
  ...properties
}: ButtonHTMLAttributes<HTMLButtonElement>): ReactNode {
  return (
    <button className={`primitive-button ${className}`.trim()} type="button" {...properties}>
      {children}
    </button>
  );
}

export function IconButton({
  children,
  label,
  ...properties
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label"> &
  Readonly<{ label: string }>): ReactNode {
  return (
    <Button aria-label={label} className="primitive-icon-button" {...properties}>
      {children}
    </Button>
  );
}

export function Link({
  children,
  ...properties
}: Readonly<ChildrenProperties & React.AnchorHTMLAttributes<HTMLAnchorElement>>): ReactNode {
  return (
    <a className="primitive-link" {...properties}>
      {children}
    </a>
  );
}

export function Field({
  children,
  controlId,
  description,
  error,
  label
}: FieldProperties): ReactNode {
  const descriptionId = description === undefined ? undefined : `${controlId}-description`;
  const errorId = error === undefined ? undefined : `${controlId}-error`;
  return (
    <div className="primitive-field">
      <label htmlFor={controlId}>{label}</label>
      {children}
      {description === undefined ? null : <small id={descriptionId}>{description}</small>}
      {error === undefined ? null : (
        <small id={errorId} role="alert">
          {error}
        </small>
      )}
    </div>
  );
}

export function Input(properties: InputHTMLAttributes<HTMLInputElement>): ReactNode {
  return <input className="primitive-input" {...properties} />;
}
export function Textarea(properties: TextareaHTMLAttributes<HTMLTextAreaElement>): ReactNode {
  return <textarea className="primitive-input" {...properties} />;
}
export function Select({
  children,
  ...properties
}: Readonly<ChildrenProperties & React.SelectHTMLAttributes<HTMLSelectElement>>): ReactNode {
  return (
    <select className="primitive-input" {...properties}>
      {children}
    </select>
  );
}
export function Combobox({
  options,
  ...properties
}: Readonly<InputHTMLAttributes<HTMLInputElement> & { options: readonly string[] }>): ReactNode {
  const listId = `combobox-${properties.name ?? properties.id ?? "options"}`;
  return (
    <>
      <input className="primitive-input" list={listId} {...properties} />
      <datalist id={listId}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </>
  );
}
export function Checkbox(properties: InputHTMLAttributes<HTMLInputElement>): ReactNode {
  return <input className="primitive-check" type="checkbox" {...properties} />;
}
export function Radio(properties: InputHTMLAttributes<HTMLInputElement>): ReactNode {
  return <input className="primitive-check" type="radio" {...properties} />;
}
export function Switch(properties: Omit<InputHTMLAttributes<HTMLInputElement>, "type">): ReactNode {
  return <input className="primitive-switch" type="checkbox" role="switch" {...properties} />;
}

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
export function Progress({ label, value }: Readonly<{ label: string; value: number }>): ReactNode {
  return (
    <label className="primitive-progress">
      {label}
      <progress max={100} value={value}>
        {value}%
      </progress>
    </label>
  );
}
export function Skeleton({ label = "Loading content" }: Readonly<{ label?: string }>): ReactNode {
  return (
    <span aria-label={label} aria-live="polite" className="primitive-skeleton" role="status" />
  );
}
export function Callout({
  children,
  tone = "information",
  title
}: Readonly<
  ChildrenProperties & { title: string; tone?: "danger" | "information" | "warning" }
>): ReactNode {
  return (
    <aside className={`primitive-callout primitive-callout--${tone}`}>
      <strong>{title}</strong>
      <div>{children}</div>
    </aside>
  );
}
export function StatusLabel({
  children,
  tone = "reviewed"
}: Readonly<
  ChildrenProperties & { tone?: "limited-evidence" | "problem" | "reviewed" | "under-review" }
>): ReactNode {
  return <span className={`primitive-status primitive-status--${tone}`}>{children}</span>;
}
export function Pagination({
  currentPage,
  onPageChange,
  pageCount
}: Readonly<{
  currentPage: number;
  onPageChange: (page: number) => void;
  pageCount: number;
}>): ReactNode {
  return (
    <nav aria-label="Pagination" className="primitive-pagination">
      <Button disabled={currentPage <= 1} onClick={() => onPageChange(currentPage - 1)}>
        Previous
      </Button>
      <span aria-current="page">
        Page {currentPage} of {pageCount}
      </span>
      <Button disabled={currentPage >= pageCount} onClick={() => onPageChange(currentPage + 1)}>
        Next
      </Button>
    </nav>
  );
}
export function FilePicker(properties: InputHTMLAttributes<HTMLInputElement>): ReactNode {
  return <input className="primitive-file" type="file" {...properties} />;
}
export function LiveRegion({ children }: ChildrenProperties): ReactNode {
  return (
    <div aria-atomic="true" aria-live="polite" className="sr-only">
      {children}
    </div>
  );
}

export function Modal({
  children,
  description,
  open,
  onOpenChange,
  title
}: Readonly<
  ChildrenProperties & {
    description: string;
    onOpenChange: (open: boolean) => void;
    open: boolean;
    title: string;
  }
>): ReactNode {
  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Portal>
        <Dialog.Backdrop className="primitive-backdrop" />
        <Dialog.Viewport className="primitive-viewport">
          <Dialog.Popup className="primitive-modal">
            <Dialog.Title>{title}</Dialog.Title>
            <Dialog.Description>{description}</Dialog.Description>
            {children}
            <Dialog.Close className="primitive-button">Close</Dialog.Close>
          </Dialog.Popup>
        </Dialog.Viewport>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function PopoverCard({
  children,
  content,
  open,
  onOpenChange,
  triggerLabel
}: Readonly<
  ChildrenProperties & {
    content: ReactNode;
    onOpenChange: (open: boolean) => void;
    open: boolean;
    triggerLabel: string;
  }
>): ReactNode {
  return (
    <Popover.Root onOpenChange={onOpenChange} open={open}>
      <Popover.Trigger className="primitive-button">{triggerLabel}</Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner>
          <Popover.Popup className="primitive-popover">{content}</Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
      {children}
    </Popover.Root>
  );
}
