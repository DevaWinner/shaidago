import type { components } from "@/lib/api/generated/schema";
import { toOpaqueSecret } from "@/lib/api/forwarded-context";
import type { ServerEnvironment } from "@/lib/config/server";

/**
 * Reviewer cookies are created and read only in server code. The session token and CSRF token are
 * both `HttpOnly`, so neither is ever available to browser JavaScript, a response body, or a log.
 * The BFF's CSRF defence is `SameSite=Lax` plus the exact-Origin check on every mutation; the
 * server-held CSRF token is forwarded to the API, which re-verifies it against the session.
 */

export type CookieNames = {
  readonly session: string;
  readonly csrf: string;
  readonly secure: boolean;
};

const MAX_COOKIE_LIFETIME_SECONDS = 31 * 24 * 60 * 60;
// RFC 6265 cookie-octet: no whitespace, quote, comma, semicolon, or backslash.
const COOKIE_VALUE_PATTERN = /^[\x21\x23-\x2b\x2d-\x3a\x3c-\x5b\x5d-\x7e]{16,512}$/;

export class SessionPolicyError extends Error {
  public readonly code = "session_policy_mismatch";

  public constructor() {
    super("session_policy_mismatch");
    this.name = "SessionPolicyError";
  }
}

/** `__Host-` cookies require Secure and Path=/, so they are used only where HTTPS is guaranteed. */
export function cookieNamesFor(appEnvironment: ServerEnvironment["appEnvironment"]): CookieNames {
  return appEnvironment === "staging" || appEnvironment === "production"
    ? { session: "__Host-sg_session", csrf: "__Host-sg_csrf", secure: true }
    : { session: "sg_session", csrf: "sg_csrf", secure: false };
}

export type ReviewerCookies = { readonly session?: string; readonly csrf?: string };

/**
 * Reads only the two reviewer cookies. A name that appears twice is discarded rather than guessed
 * at: a sibling subdomain or injected header could otherwise shadow the real value.
 */
export function readReviewerCookies(headers: Headers, names: CookieNames): ReviewerCookies {
  const seen = new Map<string, string | null>();

  for (const part of (headers.get("Cookie") ?? "").split(";")) {
    const separator = part.indexOf("=");

    if (separator < 0) {
      continue;
    }

    const name = part.slice(0, separator).trim();

    if (name === names.session || name === names.csrf) {
      seen.set(name, seen.has(name) ? null : part.slice(separator + 1).trim());
    }
  }

  const session = toOpaqueSecret(seen.get(names.session) ?? undefined);
  const csrf = toOpaqueSecret(seen.get(names.csrf) ?? undefined);

  return {
    ...(session === undefined ? {} : { session }),
    ...(csrf === undefined ? {} : { csrf })
  };
}

function serialise(name: string, value: string, maxAge: number, secure: boolean): string {
  return [
    `${name}=${value}`,
    "Path=/",
    `Max-Age=${maxAge}`,
    ...(maxAge === 0 ? ["Expires=Thu, 01 Jan 1970 00:00:00 GMT"] : []),
    "HttpOnly",
    "SameSite=Lax",
    ...(secure ? ["Secure"] : [])
  ].join("; ");
}

/**
 * Converts the API's one-time session response into the two cookies. The API's cookie policy is
 * checked, not blindly applied: a policy that would weaken the cookie (wrong name, missing Secure
 * or HttpOnly, another path, an unbounded lifetime) is refused so the caller can revoke the session.
 */
export function buildSessionCookies(
  session: components["schemas"]["SessionOut"],
  names: CookieNames
): readonly string[] {
  const policy = session.cookie;

  if (
    policy.name !== names.session ||
    policy.secure !== names.secure ||
    policy.http_only !== true ||
    policy.same_site.toLowerCase() !== "lax" ||
    policy.path !== "/" ||
    !Number.isInteger(policy.max_age_seconds) ||
    policy.max_age_seconds < 1 ||
    policy.max_age_seconds > MAX_COOKIE_LIFETIME_SECONDS ||
    !COOKIE_VALUE_PATTERN.test(session.session_token) ||
    !COOKIE_VALUE_PATTERN.test(session.csrf_token)
  ) {
    throw new SessionPolicyError();
  }

  return [
    serialise(names.session, session.session_token, policy.max_age_seconds, names.secure),
    serialise(names.csrf, session.csrf_token, policy.max_age_seconds, names.secure)
  ];
}

export function clearSessionCookies(names: CookieNames): readonly string[] {
  return [
    serialise(names.session, "", 0, names.secure),
    serialise(names.csrf, "", 0, names.secure)
  ];
}

export function withCookies(response: Response, cookies: readonly string[]): Response {
  for (const cookie of cookies) {
    response.headers.append("Set-Cookie", cookie);
  }

  return response;
}
