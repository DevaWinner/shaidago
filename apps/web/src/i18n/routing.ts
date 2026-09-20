import { defineRouting } from "next-intl/routing";

import type { ApiLocale } from "@/lib/api/forwarded-context";

export const LOCALES = ["en", "ha", "ig", "yo"] as const satisfies readonly ApiLocale[];
export const DEFAULT_LOCALE: ApiLocale = "en";

/**
 * Locales whose interface copy has been written and reviewed. A locale outside this list still has
 * its routes, but its pages declare the language they truly contain and say that no reviewed
 * translation exists, rather than presenting English text as Hausa, Igbo, or Yoruba. Add a locale
 * here only when fluent, reviewed copy for every critical string exists (FE-051 records who).
 */
export const REVIEWED_LOCALES: readonly ApiLocale[] = ["en"];

const deployed = process.env["APP_ENV"] === "staging" || process.env["APP_ENV"] === "production";

/**
 * Every public route is locale-prefixed. Negotiation reads only the language-preference cookie and
 * the `Accept-Language` header, in that order, and falls back to English. The cookie holds one of
 * the four locale codes: no identifier and no personal data.
 */
export const routing = defineRouting({
  locales: LOCALES,
  defaultLocale: DEFAULT_LOCALE,
  localePrefix: "always",
  localeCookie: {
    name: "NEXT_LOCALE",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
    path: "/",
    secure: deployed
  }
});

export function isSupportedLocale(value: unknown): value is ApiLocale {
  return LOCALES.some((locale) => locale === value);
}

/** The language a page's text is actually written in for a requested route locale. */
export function contentLocale(locale: ApiLocale): ApiLocale {
  return REVIEWED_LOCALES.includes(locale) ? locale : DEFAULT_LOCALE;
}
