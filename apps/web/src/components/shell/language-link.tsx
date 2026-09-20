"use client";

import { useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/ui/overlay";
import { hasUnsavedDraft } from "@/lib/draft-guard";

export const LANGUAGE_SWITCH_FLAG = "sg-language-switched";

export type DraftGuardCopy = Readonly<{
  body: string;
  leave: string;
  stay: string;
  title: string;
}>;

function markSwitch(language: string): void {
  try {
    // One word for the next page's announcement; never any content, and gone with the tab.
    sessionStorage.setItem(LANGUAGE_SWITCH_FLAG, language);
  } catch {
    // Storage can be blocked; the page still announces itself by its title and language.
  }
}

/**
 * A normal link that works with no JavaScript. With JavaScript it also warns before leaving a page
 * that holds an unsaved private draft (the draft is never put in the URL), and marks the switch so
 * the next page can announce it.
 */
export function LanguageLink({
  children,
  className,
  guard,
  href,
  language,
  lang
}: Readonly<{
  children: ReactNode;
  className: string;
  guard: DraftGuardCopy;
  href: string;
  /** The language being switched to, so the next page can confirm it. */
  language: string;
  lang: string;
}>): ReactNode {
  const [asking, setAsking] = useState(false);

  return (
    <>
      <a
        className={className}
        href={href}
        hrefLang={language}
        lang={lang}
        onClick={(event) => {
          if (hasUnsavedDraft()) {
            event.preventDefault();
            setAsking(true);

            return;
          }

          markSwitch(language);
        }}
      >
        {children}
      </a>
      <ConfirmDialog
        cancelLabel={guard.stay}
        confirmLabel={guard.leave}
        description={guard.body}
        destructive
        onConfirm={() => {
          markSwitch(language);
          window.location.assign(href);
        }}
        onOpenChange={setAsking}
        open={asking}
        title={guard.title}
      />
    </>
  );
}
