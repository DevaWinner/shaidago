import type { ApiProblem, ApiUnavailableReason } from "@/lib/api/server";
import { BodyRejectedError } from "@/lib/bff/body";

export const BFF_PROBLEM_CODES = [
  "origin_forbidden",
  "csrf_invalid",
  "payload_too_large",
  "unsupported_media_type",
  "invalid_json",
  "bad_request",
  "idempotency_key_invalid",
  "request_aborted",
  "upstream_timeout",
  "dependency_unavailable",
  "internal_error"
] as const;

export type BffProblemCode = (typeof BFF_PROBLEM_CODES)[number];

const MACHINE_CODE_PATTERN = /^[a-z][a-z0-9_]{1,63}$/;
const MAX_RETRY_AFTER_SECONDS = 3600;

// English is a fallback for clients that cannot localise; the stable `code` is the contract and
// each locale renders its own text from it (FE-053).
const FALLBACK_TITLES: Readonly<Record<string, string>> = {
  origin_forbidden: "Request not allowed",
  csrf_invalid: "Request not allowed",
  payload_too_large: "Request too large",
  unsupported_media_type: "Unsupported content type",
  invalid_json: "Request could not be read",
  bad_request: "Request could not be read",
  idempotency_key_invalid: "Request could not be read",
  request_aborted: "Request cancelled",
  upstream_timeout: "The service took too long",
  dependency_unavailable: "The service is unavailable",
  rate_limited: "Too many requests",
  not_found: "Not found",
  validation_failed: "Some details need attention"
};

export type BrowserProblemInit = {
  readonly status: number;
  readonly code: string;
  readonly requestId: string;
  readonly retryAfterSeconds?: number | undefined;
  readonly fieldErrors?: readonly { readonly field: string; readonly code: string }[] | undefined;
};

/** Headers every private or error response carries: never stored by a browser, proxy, or CDN. */
export function noStoreHeaders(requestId: string): Headers {
  return new Headers({ "Cache-Control": "no-store", "X-Request-Id": requestId });
}

/**
 * The only shape a browser ever receives for a failure: stable code, safe title, request ID, and
 * field paths with rule codes. Backend `detail`, submitted values, hostnames, and stack data have
 * no path into it.
 */
export function problemResponse(init: BrowserProblemInit): Response {
  const code = MACHINE_CODE_PATTERN.test(init.code) ? init.code : "internal_error";
  const headers = noStoreHeaders(init.requestId);
  headers.set("Content-Type", "application/problem+json");

  if (
    init.retryAfterSeconds !== undefined &&
    Number.isInteger(init.retryAfterSeconds) &&
    init.retryAfterSeconds >= 0 &&
    init.retryAfterSeconds <= MAX_RETRY_AFTER_SECONDS
  ) {
    headers.set("Retry-After", String(init.retryAfterSeconds));
  }

  return new Response(
    JSON.stringify({
      type: "about:blank",
      title: FALLBACK_TITLES[code] ?? "Request failed",
      status: init.status,
      code,
      request_id: init.requestId,
      ...(init.fieldErrors !== undefined && init.fieldErrors.length > 0
        ? { errors: init.fieldErrors.map(({ field, code: rule }) => ({ field, code: rule })) }
        : {})
    }),
    { status: init.status, headers }
  );
}

export function apiProblemResponse(problem: ApiProblem): Response {
  return problemResponse({
    status: problem.status,
    code: problem.code,
    requestId: problem.requestId,
    retryAfterSeconds: problem.retryAfterSeconds,
    fieldErrors: problem.fieldErrors
  });
}

export function unavailableResponse(reason: ApiUnavailableReason, requestId: string): Response {
  switch (reason) {
    case "timeout":
      return problemResponse({ status: 504, code: "upstream_timeout", requestId });
    case "aborted":
      return abortedResponse(requestId);
    case "network":
    case "malformed_response":
      return problemResponse({ status: 503, code: "dependency_unavailable", requestId });
  }
}

export function bodyRejectedResponse(error: BodyRejectedError, requestId: string): Response {
  switch (error.reason) {
    case "payload_too_large":
      return problemResponse({ status: 413, code: "payload_too_large", requestId });
    case "unsupported_media_type":
      return problemResponse({ status: 415, code: "unsupported_media_type", requestId });
    case "invalid_json":
      return problemResponse({ status: 400, code: "invalid_json", requestId });
  }
}

/** 499 is the conventional "client closed request"; nothing is forwarded or retried after it. */
export function abortedResponse(requestId: string): Response {
  return problemResponse({ status: 499, code: "request_aborted", requestId });
}
