import { buildForwardedHeaders, type ForwardedContext } from "@/lib/api/forwarded-context";
import { toIdempotencyKey } from "@/lib/bff/idempotency";

/**
 * The complete set of headers the BFF may ever send to the private API. The browser's `Cookie`,
 * `Authorization`, `Host`, `Content-Length`, `X-Forwarded-*`, and every other header are absent by
 * construction: headers are assembled from validated values, never copied from the request.
 * `Authorization` is added by the server-only transport, not here.
 */
export const BACKEND_HEADER_ALLOWLIST = [
  "x-request-id",
  "x-shaidago-locale",
  "x-shaidago-client-hmac",
  "idempotency-key",
  "content-type",
  "x-shaidago-session",
  "x-shaidago-csrf"
] as const;

const OPAQUE_SECRET_PATTERN = /^[\x21-\x7e]{16,512}$/;

export type BackendRequestInput = {
  readonly context: ForwardedContext;
  readonly contentType?: "application/json" | "multipart/form-data";
  /** For multipart, the exact value including the boundary, validated by the body guard. */
  readonly multipartContentType?: string;
  readonly idempotencyKey?: unknown;
  readonly session?: unknown;
  readonly csrf?: unknown;
};

export class BackendRequestError extends Error {
  public constructor(public readonly reason: "idempotency_key_invalid") {
    super(reason);
    this.name = "BackendRequestError";
  }
}

export function buildBackendHeaders(
  input: BackendRequestInput,
  generateRequestId: () => string
): { readonly headers: Record<string, string>; readonly requestId: string } {
  const { headers, requestId } = buildForwardedHeaders(input.context, generateRequestId);

  if (input.contentType === "application/json") {
    headers["Content-Type"] = "application/json";
  } else if (
    input.multipartContentType !== undefined &&
    /^multipart\/form-data;/i.test(input.multipartContentType)
  ) {
    headers["Content-Type"] = input.multipartContentType;
  }

  if (input.idempotencyKey !== undefined) {
    const key = toIdempotencyKey(input.idempotencyKey);

    if (key === undefined) {
      throw new BackendRequestError("idempotency_key_invalid");
    }

    headers["Idempotency-Key"] = key;
  }

  if (typeof input.session === "string" && OPAQUE_SECRET_PATTERN.test(input.session)) {
    headers["X-Shaidago-Session"] = input.session;
  }

  if (typeof input.csrf === "string" && OPAQUE_SECRET_PATTERN.test(input.csrf)) {
    headers["X-Shaidago-Csrf"] = input.csrf;
  }

  return { headers, requestId };
}

export type AbortKind = "client_aborted" | "timeout";

/** One signal that ends on client disconnect or the operation's timeout, whichever comes first. */
export function backendSignal(request: Request, timeoutMs: number): AbortSignal {
  return AbortSignal.any([request.signal, AbortSignal.timeout(timeoutMs)]);
}

export function classifyAbort(request: Request): AbortKind {
  return request.signal.aborted ? "client_aborted" : "timeout";
}
