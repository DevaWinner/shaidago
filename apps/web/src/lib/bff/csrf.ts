import { timingSafeEqual } from "node:crypto";

const CSRF_TOKEN_PATTERN = /^[A-Za-z0-9_-]{32,128}$/;

export type CsrfCheck = { readonly ok: true } | { readonly ok: false };

/**
 * Compares the token the browser presented with the one held server-side for the session, in
 * constant time. Both must be well formed; the BFF never logs or echoes either. This is a
 * transport-agnostic verifier: the reviewer-session handlers decide where each value comes from.
 * The API independently re-checks the token against the session (`403 csrf_invalid`).
 */
export function verifyCsrfToken(presented: unknown, expected: unknown): CsrfCheck {
  if (
    typeof presented !== "string" ||
    typeof expected !== "string" ||
    !CSRF_TOKEN_PATTERN.test(presented) ||
    !CSRF_TOKEN_PATTERN.test(expected)
  ) {
    return { ok: false };
  }

  const presentedBytes = Buffer.from(presented);
  const expectedBytes = Buffer.from(expected);

  return presentedBytes.length === expectedBytes.length &&
    timingSafeEqual(presentedBytes, expectedBytes)
    ? { ok: true }
    : { ok: false };
}
