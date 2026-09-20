import "server-only";

import { serverApi } from "@/lib/api/server";
import { loadServerEnvironment } from "@/lib/config/server";
import { BodyRejectedError, readBoundedJson } from "@/lib/bff/body";
import { guardMutation } from "@/lib/bff/guard";
import {
  apiProblemResponse,
  bodyRejectedResponse,
  noStoreHeaders,
  problemResponse,
  unavailableResponse
} from "@/lib/bff/problem";
import { originPolicyFor } from "@/lib/bff/public-handler";
import { signInInput } from "@/lib/bff/reviewer-schemas";
import {
  SessionPolicyError,
  buildSessionCookies,
  clearSessionCookies,
  cookieNamesFor,
  readReviewerCookies,
  withCookies
} from "@/lib/bff/reviewer-session";
import { forwardedContextFor } from "@/lib/bff/request-context";

const SIGN_IN_MAX_BYTES = 2 * 1024;

/**
 * Sign-in is the only place the API's one-time `session_token` and `csrf_token` exist in the BFF.
 * They go straight into `HttpOnly` cookies; the browser response carries neither token nor the
 * cookie policy, only what the UI needs to show (role and expiry).
 */
export async function handleSignIn(request: Request): Promise<Response> {
  const requestId = crypto.randomUUID();

  try {
    const names = cookieNamesFor(loadServerEnvironment().appEnvironment);
    const guard = guardMutation(request, {
      policy: originPolicyFor(request),
      requestId,
      body: { rule: "json", maxBytes: SIGN_IN_MAX_BYTES }
    });

    if (!guard.ok) {
      return guard.response;
    }

    const input = signInInput.safeParse(await readBoundedJson(request, SIGN_IN_MAX_BYTES));

    if (!input.success) {
      // Field paths only: a submitted identifier or password never appears in a response.
      return problemResponse({
        status: 422,
        code: "validation_failed",
        requestId,
        fieldErrors: input.error.issues.map((issue) => ({
          field: ["body", ...issue.path.map(String)].join("."),
          code: issue.code
        }))
      });
    }

    const api = serverApi();
    const result = await api.signIn(input.data, {
      context: forwardedContextFor(request, requestId),
      signal: request.signal
    });

    if (result.kind === "problem") {
      return apiProblemResponse(result.problem);
    }

    if (result.kind !== "ok") {
      return result.kind === "unavailable"
        ? unavailableResponse(result.reason, result.requestId)
        : problemResponse({ status: 503, code: "dependency_unavailable", requestId });
    }

    const session = result.data;

    try {
      const cookies = buildSessionCookies(session, names);
      const headers = noStoreHeaders(requestId);
      headers.set("Content-Type", "application/json");

      return withCookies(
        new Response(
          JSON.stringify({
            reviewer: { role: session.reviewer.role },
            expires_at: session.expires_at,
            idle_timeout_seconds: session.idle_timeout_seconds
          }),
          { status: 201, headers }
        ),
        cookies
      );
    } catch (error) {
      if (!(error instanceof SessionPolicyError)) {
        throw error;
      }

      // The API issued a session we refuse to store. Revoke it (best effort) rather than orphan it.
      await api
        .signOut({
          context: { requestId },
          session: session.session_token,
          csrf: session.csrf_token
        })
        .catch(() => undefined);

      return problemResponse({ status: 503, code: "dependency_unavailable", requestId });
    }
  } catch (error) {
    if (error instanceof BodyRejectedError) {
      return bodyRejectedResponse(error, requestId);
    }

    return problemResponse({ status: 500, code: "internal_error", requestId });
  }
}

/**
 * Sign-out always clears the browser cookies, whether the API session was revoked, already gone,
 * or unreachable. An unreachable API is still reported so the UI does not claim a revocation.
 */
export async function handleSignOut(request: Request): Promise<Response> {
  const requestId = crypto.randomUUID();

  try {
    const names = cookieNamesFor(loadServerEnvironment().appEnvironment);
    const cookies = readReviewerCookies(request.headers, names);
    const cleared = clearSessionCookies(names);
    const guard = guardMutation(request, {
      policy: originPolicyFor(request),
      requestId,
      body: { rule: "empty", maxBytes: 0 },
      ...(cookies.session === undefined
        ? {}
        : { csrf: { presented: cookies.csrf, expected: cookies.csrf } })
    });

    if (!guard.ok) {
      return guard.response;
    }

    const empty = () =>
      withCookies(new Response(null, { status: 204, headers: noStoreHeaders(requestId) }), cleared);

    if (cookies.session === undefined) {
      return empty();
    }

    const result = await serverApi().signOut({
      context: forwardedContextFor(request, requestId),
      signal: request.signal,
      session: cookies.session,
      csrf: cookies.csrf
    });

    if (result.kind === "ok" || (result.kind === "problem" && result.problem.status === 401)) {
      return empty();
    }

    return withCookies(
      result.kind === "problem"
        ? apiProblemResponse(result.problem)
        : result.kind === "unavailable"
          ? unavailableResponse(result.reason, result.requestId)
          : problemResponse({ status: 503, code: "dependency_unavailable", requestId }),
      cleared
    );
  } catch {
    return problemResponse({ status: 500, code: "internal_error", requestId });
  }
}
