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
  /** Runs after the Origin check and before CSRF, e.g. to answer 401 before 403. */
  readonly afterOrigin?: () => Response | undefined;
  /** True when the operation requires (and the handler will forward) an idempotency key. */
  readonly requireIdempotencyKey?: boolean;
};

export type GuardResult =
  | { readonly ok: true; readonly idempotencyKey: string | undefined }
  | { readonly ok: false; readonly response: Response };

/**
 * Empty-body operations refuse a declared or chunked body. The framework hands every handler a
 * body stream object even when nothing was sent, so its mere presence proves nothing; what matters
 * is that these handlers never read or forward a body, so an undeclared one has no effect.
 */
function emptyBodyRejected(request: Request): boolean {
  const declared = request.headers.get("Content-Length");

  return request.headers.has("Transfer-Encoding") || (declared !== null && declared !== "0");
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

  const early = options.afterOrigin?.();

  if (early !== undefined) {
    return { ok: false, response: early };
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
      if (emptyBodyRejected(request)) {
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
