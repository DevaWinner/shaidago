"use client";

import { useEffect, useRef, type ReactNode } from "react";

export type SummaryItem = Readonly<{ controlId: string; message: string }>;

/**
 * The form-level error list. When errors appear it takes focus (so a keyboard or screen-reader user
 * lands on it after a failed submit), states how many problems there are, and links each message to
 * its control: activating a link moves focus to that field. It renders nothing when there are none.
 * Each message is also associated with its own field by `Field`, so the summary is a shortcut, not
 * the only place the error is exposed.
 */
export function ErrorSummary({
  extra = [],
  items,
  title
}: Readonly<{
  /** Messages with no control, such as a whole-request problem. */
  extra?: readonly string[];
  items: readonly SummaryItem[];
  title: string;
}>): ReactNode {
  const heading = useRef<HTMLHeadingElement>(null);
  const count = items.length + extra.length;

  useEffect(() => {
    if (count > 0) {
      heading.current?.focus();
    }
  }, [count]);

  if (count === 0) {
    return null;
  }

  return (
    <div
      className="grid gap-2 rounded-ledger-control border-2 border-destructive bg-card p-4"
      data-slot="error-summary"
      role="alert"
    >
      <h2 className="m-0 text-ledger-lg" ref={heading} tabIndex={-1}>
        {title}
      </h2>
      <ul className="m-0 grid list-none gap-1 p-0">
        {items.map((item) => (
          <li key={item.controlId}>
            <a
              className="font-semibold text-destructive underline"
              href={`#${item.controlId}`}
              onClick={(event) => {
                const control = document.getElementById(item.controlId);

                if (control !== null) {
                  // A hash link scrolls but does not always focus a form control in every browser.
                  event.preventDefault();
                  control.focus();
                }
              }}
            >
              {item.message}
            </a>
          </li>
        ))}
        {extra.map((message) => (
          <li key={message}>{message}</li>
        ))}
      </ul>
    </div>
  );
}
