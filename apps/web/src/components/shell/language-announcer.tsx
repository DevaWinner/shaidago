"use client";

import { useEffect, useState, type ReactNode } from "react";

import { LANGUAGE_SWITCH_FLAG } from "@/components/shell/language-link";

const VISIBLE_MS = 8000;

/**
 * After a language switch, confirms it in words: the message sits in the shell's polite status
 * region, so screen readers announce it and sighted users see it. It reads and clears a one-word
 * flag left by the link, and only speaks when the flag matches the language of this page.
 */
export function LanguageAnnouncer({
  current,
  language,
  languageName,
  template
}: Readonly<{
  current: string;
  /** The language the message text is written in (English when its copy is not yet translated). */
  language: string;
  languageName: string;
  template: string;
}>): ReactNode {
  const [message, setMessage] = useState<string | undefined>(undefined);

  useEffect(() => {
    let switched: string | null = null;

    try {
      switched = sessionStorage.getItem(LANGUAGE_SWITCH_FLAG);
      sessionStorage.removeItem(LANGUAGE_SWITCH_FLAG);
    } catch {
      return undefined;
    }

    if (switched !== current) {
      return undefined;
    }

    const text = template.replace("{language}", languageName);
    // Deferred so the state update is not a synchronous cascade inside the effect.
    const show = window.setTimeout(() => {
      setMessage(text);
    }, 0);
    const hide = window.setTimeout(() => {
      setMessage(undefined);
    }, VISIBLE_MS);

    return () => {
      window.clearTimeout(show);
      window.clearTimeout(hide);
    };
  }, [current, languageName, template]);

  return message === undefined ? null : <span lang={language}>{message}</span>;
}
