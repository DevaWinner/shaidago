import { createTranslator } from "next-intl";

import type { ApiLocale } from "@/lib/api/forwarded-context";

// Kept apart from the catalogue so a client component can format a message without pulling every
// language's copy into its bundle.
/** Formats one ICU message from a catalogue with real plural and number rules for its language. */
export function formatMessage(
  language: ApiLocale,
  template: string,
  values: Readonly<Record<string, string | number>>
): string {
  const translator = createTranslator({ locale: language, messages: { message: template } });

  return translator("message", { ...values });
}
