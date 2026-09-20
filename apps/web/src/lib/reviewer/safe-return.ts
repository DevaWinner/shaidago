import type { ApiLocale } from "@/lib/api/forwarded-context";

const REPORT_ID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

/** Where a reviewer lands after signing in when nothing else was asked for. */
export function queuePath(locale: ApiLocale): string {
  return `/${locale}/reviewer/reports`;
}

/**
 * The only return targets sign-in will honour: this locale's queue, or one report in it. The value
 * is matched against an exact allowlist and the result is rebuilt from the matched parts, so an
 * absolute URL, a protocol-relative `//host`, a backslash, another locale, another route, or any
 * query or fragment can never become a redirect. Nothing else from the address is ever kept.
 */
export function safeReviewerTarget(locale: ApiLocale, value: unknown): string | undefined {
  if (typeof value !== "string" || value.length > 200) {
    return undefined;
  }

  const match = new RegExp(`^/${locale}/reviewer/reports(?:/(${REPORT_ID}))?$`, "i").exec(value);

  if (match === null) {
    return undefined;
  }

  return match[1] === undefined
    ? queuePath(locale)
    : `${queuePath(locale)}/${match[1].toLowerCase()}`;
}

export const SIGN_IN_REASONS = ["expired", "signed_out"] as const;
export type SignInReason = (typeof SIGN_IN_REASONS)[number];

export function toSignInReason(value: unknown): SignInReason | undefined {
  return SIGN_IN_REASONS.find((reason) => reason === value);
}

/** Sign-in address for a locale, optionally carrying an allowlisted reason and return target. */
export function signInPath(
  locale: ApiLocale,
  options: { reason?: SignInReason; next?: string } = {}
): string {
  const parameters = new URLSearchParams();
  const next = safeReviewerTarget(locale, options.next);

  if (options.reason !== undefined) {
    parameters.set("reason", options.reason);
  }
  if (next !== undefined && next !== queuePath(locale)) {
    parameters.set("next", next);
  }

  const query = parameters.toString();

  return `/${locale}/reviewer/sign-in${query === "" ? "" : `?${query}`}`;
}
