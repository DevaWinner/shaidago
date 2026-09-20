import { defineRouting } from "next-intl/routing";

import status from "../../messages/status.json";
import type { ApiLocale } from "@/lib/api/forwarded-context";

export const LOCALES = ["en", "ha", "ig", "yo"] as const satisfies readonly ApiLocale[];
export const DEFAULT_LOCALE: ApiLocale = "en";

type StatusFile = {
  domains: Record<string, { critical: boolean }>;
  locales: Record<string, Record<string, { status: string }>>;
};

const translationStatus: StatusFile = status;

export function isSupportedLocale(value: unknown): value is ApiLocale {
  return LOCALES.some((locale) => locale === value);
}

/** Whether a domain's copy for a locale has a named human reviewer's approval (`messages/status.json`). */
export function isDomainReviewed(locale: ApiLocale, domain: string): boolean {
  return translationStatus.locales[locale]?.[domain]?.status === "reviewed";
}

/**
 * A locale is served as its own language only when every critical domain (safety, status, shell,
 * recovery) is reviewed; the parity check keeps that file consistent with the catalogues. A locale
 * outside this list still has its routes, but its pages declare the language they truly contain and
 * say that no reviewed translation exists, rather than presenting English text as Hausa, Igbo, or
 * Yoruba.
 */
export const REVIEWED_LOCALES: readonly ApiLocale[] = LOCALES.filter((locale) =>
  Object.entries(translationStatus.domains)
    .filter(([, meta]) => meta.critical)
    .every(([domain]) => isDomainReviewed(locale, domain))
);

/** The language a page's text is actually written in for a requested route locale. */
export function contentLocale(locale: ApiLocale): ApiLocale {
  return REVIEWED_LOCALES.includes(locale) ? locale : DEFAULT_LOCALE;
}

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
