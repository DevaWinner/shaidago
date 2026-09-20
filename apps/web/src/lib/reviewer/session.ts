import "server-only";

import type { Route } from "next";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";

import type { ApiLocale } from "@/lib/api/forwarded-context";
import type { ApiResult, ReviewerOptions } from "@/lib/api/server";
import { forwardedContextForHeaders } from "@/lib/bff/request-context";
import { cookieNamesFor, readReviewerCookies } from "@/lib/bff/reviewer-session";
import { loadServerEnvironment } from "@/lib/config/server";
import { signInPath } from "@/lib/reviewer/safe-return";

/**
 * Reviewer Server Components read the HttpOnly session cookie here, on the server only. The token
 * is put in a request-scoped options object that is handed to the private API and never rendered,
 * serialised into a client prop, or logged. A missing cookie means "sign in", without any API call.
 */
export async function reviewerOptionsFor(locale: ApiLocale): Promise<ReviewerOptions | undefined> {
  const names = cookieNamesFor(loadServerEnvironment().appEnvironment);
  const [cookieStore, headerStore] = await Promise.all([cookies(), headers()]);
  const cookieHeader = cookieStore
    .getAll()
    .map(({ name, value }) => `${name}=${value}`)
    .join("; ");
  const parsed = readReviewerCookies(new Headers({ Cookie: cookieHeader }), names);

  if (parsed.session === undefined) {
    return undefined;
  }

  return {
    context: { ...forwardedContextForHeaders(headerStore, crypto.randomUUID()), locale },
    session: parsed.session,
    ...(parsed.csrf === undefined ? {} : { csrf: parsed.csrf })
  };
}

/** The signed-out redirect, with the safe return target so sign-in can bring the reviewer back. */
export function redirectToSignIn(
  locale: ApiLocale,
  reason: "expired" | undefined,
  next: string | undefined
): never {
  redirect(
    // Proof: `signInPath` builds a same-origin path from the locale and an allowlisted target.
    signInPath(locale, {
      ...(reason === undefined ? {} : { reason }),
      ...(next === undefined ? {} : { next })
    }) as Route
  );
}

/**
 * Turns an API result for a reviewer read into a page decision. A `401` is an expired or revoked
 * session, so the page discards everything it fetched and redirects to sign-in; nothing private
 * is kept for the sign-in screen. Every other outcome is returned for the page to render.
 */
export function requireSession<T>(
  result: ApiResult<T>,
  locale: ApiLocale,
  next: string
): ApiResult<T> {
  if (result.kind === "problem" && result.problem.status === 401) {
    redirectToSignIn(locale, "expired", next);
  }

  return result;
}
