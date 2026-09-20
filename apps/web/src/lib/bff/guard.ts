import { toIdempotencyKey } from "@/lib/bff/idempotency";
import { BodyRejectedError, preflightBody, type ContentTypeRule } from "@/lib/bff/body";
import { checkOrigin, type OriginPolicy } from "@/lib/bff/origin";
import { verifyCsrfToken } from "@/lib/bff/csrf";
import { bodyRejectedResponse, problemResponse } from "@/lib/bff/problem";

export type MutationGuardOptions = {
  readonly policy: OriginPolicy;
  readonly requestId: string;
  readonly body: { readonly rule: ContentTypeRule | "empty"; readonly maxBytes: number };
  /** Present only for cookie-authenticated reviewer mutations; both values are server-resolved. */
  readonly csrf?: { readonly presented: unknown; readonly expected: unknown };
  /** True when the operation requires (and the handler will forward) an idempotency key. */
  readonly requireIdempotencyKey?: boolean;
};

export type GuardResult =
  | { readonly ok: true; readonly idempotencyKey: string | undefined }
  | { readonly ok: false; readonly response: Response };

function emptyBodyRejected(headers: Headers): boolean {
  const declared = headers.get("Content-Length");

  return headers.has("Transfer-Encoding") || (declared !== null && declared !== "0");
}

/**
 * Runs the checks that must precede reading or forwarding a body, in order: Origin, CSRF, then
 * header-only body preflight and idempotency-key validation. Nothing is parsed or forwarded here.
 */
export function guardMutation(request: Request, options: MutationGuardOptions): GuardResult {
  const { requestId } = options;

  if (!checkOrigin(request.headers, options.policy).ok) {
    return {
      ok: false,
      response: problemResponse({ status: 403, code: "origin_forbidden", requestId })
    };
  }

  if (
    options.csrf !== undefined &&
    !verifyCsrfToken(options.csrf.presented, options.csrf.expected).ok
  ) {
    return {
      ok: false,
      response: problemResponse({ status: 403, code: "csrf_invalid", requestId })
    };
  }

  try {
    if (options.body.rule === "empty") {
      if (emptyBodyRejected(request.headers)) {
        throw new BodyRejectedError("payload_too_large");
      }
    } else {
      preflightBody(request.headers, options.body.rule, options.body.maxBytes);
    }
  } catch (error) {
    if (error instanceof BodyRejectedError) {
      return { ok: false, response: bodyRejectedResponse(error, requestId) };
    }

    throw error;
  }

  if (options.requireIdempotencyKey === true) {
    const key = toIdempotencyKey(request.headers.get("Idempotency-Key"));

    if (key === undefined) {
      return {
        ok: false,
        response: problemResponse({ status: 400, code: "idempotency_key_invalid", requestId })
      };
    }

    return { ok: true, idempotencyKey: key };
  }

  return { ok: true, idempotencyKey: undefined };
}
