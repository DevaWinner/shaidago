import en from "../../messages/en.json";
import ha from "../../messages/ha.json";
import ig from "../../messages/ig.json";
import yo from "../../messages/yo.json";
import { DEFAULT_LOCALE, isDomainReviewed } from "@/i18n/routing";
import type { ApiLocale } from "@/lib/api/forwarded-context";

/** The English source shape; every other catalogue has exactly these keys (see `messages:check`). */
export type Messages = typeof en;
export type Domain = keyof Messages;

const CATALOGUES: Readonly<Record<ApiLocale, unknown>> = { en, ha, ig, yo };

export type DomainCopy<D extends Domain> = Readonly<{
  messages: Messages[D];
  /** The language the returned text is written in. */
  language: ApiLocale;
  /** True when the requested locale had no reviewed copy and the English original is returned. */
  isOriginal: boolean;
}>;

function isComplete(node: unknown): boolean {
  if (node === null || node === undefined) {
    return false;
  }

  return typeof node === "object"
    ? Object.values(node as Record<string, unknown>).every(isComplete)
    : typeof node === "string" && node.trim() !== "";
}

/**
 * Returns a locale's copy for one domain only when it is marked reviewed and has no gaps; otherwise
 * the English original, flagged. The flag is never dropped: callers render a visible notice and the
 * correct `lang`, so a fallback is never silent. A domain missing from English is a build error.
 */
export function resolveDomain<D extends Domain>(locale: ApiLocale, domain: D): DomainCopy<D> {
  const candidate = (CATALOGUES[locale] as Record<string, unknown>)[domain];

  if (locale !== DEFAULT_LOCALE && isDomainReviewed(locale, domain) && isComplete(candidate)) {
    // Proof: `messages:check` enforces identical keys and ICU variables for every catalogue, and
    // `isComplete` has just confirmed no key is pending.
    return { messages: candidate as Messages[D], language: locale, isOriginal: false };
  }

  return { messages: en[domain], language: DEFAULT_LOCALE, isOriginal: locale !== DEFAULT_LOCALE };
}

export { formatMessage } from "@/i18n/format-message";
