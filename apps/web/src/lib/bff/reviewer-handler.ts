import "server-only";

import type { z } from "zod";

import type { ApiResult, EvidenceStream, ReviewerOptions, ServerApi } from "@/lib/api/server";
import { serverApi } from "@/lib/api/server";
import { loadServerEnvironment } from "@/lib/config/server";
import { BodyRejectedError, readBoundedJson } from "@/lib/bff/body";
import { guardMutation } from "@/lib/bff/guard";
import {
  apiProblemResponse,
  bodyRejectedResponse,
  noStoreHeaders,
  problemResponse
} from "@/lib/bff/problem";
import { originPolicyFor, resultResponse } from "@/lib/bff/public-handler";
import { idParam } from "@/lib/bff/reviewer-schemas";
import {
  clearSessionCookies,
  cookieNamesFor,
  readReviewerCookies,
  withCookies,
  type CookieNames
} from "@/lib/bff/reviewer-session";

/**
 * Shared plumbing for reviewer Route Handlers. The BFF only turns cookies into the two headers the
 * API expects and shapes errors: it never inspects a role, report state, or publication rule.
 * Every response is `no-store`, and no request body, cookie, ID, or evidence byte is logged.
 */

type Resolved = {
  readonly requestId: string;
  readonly names: CookieNames;
  readonly session: string | undefined;
  readonly csrf: string | undefined;
};

function resolve(request: Request): Resolved {
  const names = cookieNamesFor(loadServerEnvironment().appEnvironment);
  const cookies = readReviewerCookies(request.headers, names);

  return { requestId: crypto.randomUUID(), names, session: cookies.session, csrf: cookies.csrf };
}

function unauthenticated(resolved: Resolved): Response {
  // A missing or dead session sends the client to sign-in; stale cookies are cleared with it.
  return withCookies(
    problemResponse({ status: 401, code: "unauthenticated", requestId: resolved.requestId }),
    clearSessionCookies(resolved.names)
  );
}

function notFound(requestId: string): Response {
  // A malformed identifier is indistinguishable from an unknown one and never reaches the API.
  return problemResponse({ status: 404, code: "not_found", requestId });
}

function reviewerOptions(
  request: Request,
  resolved: Resolved,
  session: string,
  withCsrf: boolean
): ReviewerOptions {
  return {
    context: { requestId: resolved.requestId, locale: request.headers.get("X-Shaidago-Locale") },
    signal: request.signal,
    session,
    csrf: withCsrf ? resolved.csrf : undefined
  };
}

/** Maps a result, clearing the browser cookies when the API says the session is no longer usable. */
export function reviewerResultResponse<TData>(
  result: ApiResult<TData>,
  names: CookieNames
): Response {
  if (result.kind === "problem" && result.problem.status === 401) {
    return withCookies(apiProblemResponse(result.problem), clearSessionCookies(names));
  }

  return resultResponse(result);
}

/** Validates every path parameter as a UUID; returns undefined if any is malformed. */
export async function parseIds<TKeys extends string>(
  params: Promise<Readonly<Record<TKeys, string>>>
): Promise<Readonly<Record<TKeys, string>> | undefined> {
  const values = await params;

  for (const value of Object.values<string>(values)) {
    if (!idParam.safeParse(value).success) {
      return undefined;
    }
  }

  return values;
}

export type ReviewerJsonSpec<TIds extends string, TInput, TData> = {
  readonly schema: z.ZodType<TInput>;
  readonly maxBodyBytes: number;
  readonly call: (
    api: ServerApi,
    ids: Readonly<Record<TIds, string>>,
    input: TInput,
    options: ReviewerOptions
  ) => Promise<ApiResult<TData>>;
};

/** A cookie-authenticated JSON mutation: Origin, then session (401), then CSRF, then body. */
export async function handleReviewerJson<TIds extends string, TInput, TData>(
  request: Request,
  params: Promise<Readonly<Record<TIds, string>>>,
  spec: ReviewerJsonSpec<TIds, TInput, TData>
): Promise<Response> {
  let resolved: Resolved | undefined;

  try {
    resolved = resolve(request);
    const current = resolved;
    const guard = guardMutation(request, {
      policy: originPolicyFor(request),
      requestId: current.requestId,
      body: { rule: "json", maxBytes: spec.maxBodyBytes },
      afterOrigin: () => (current.session === undefined ? unauthenticated(current) : undefined),
      csrf: { presented: current.csrf, expected: current.csrf }
    });

    if (!guard.ok) {
      return guard.response;
    }

    const ids = await parseIds(params);

    if (ids === undefined || current.session === undefined) {
      return notFound(current.requestId);
    }

    const input = spec.schema.safeParse(await readBoundedJson(request, spec.maxBodyBytes));

    if (!input.success) {
      return problemResponse({
        status: 422,
        code: "validation_failed",
        requestId: current.requestId,
        fieldErrors: input.error.issues.map((issue) => ({
          field: ["body", ...issue.path.map(String)].join("."),
          code: issue.code
        }))
      });
    }

    return reviewerResultResponse(
      await spec.call(
        serverApi(),
        ids,
        input.data,
        reviewerOptions(request, current, current.session, true)
      ),
      current.names
    );
  } catch (error) {
    if (error instanceof BodyRejectedError && resolved !== undefined) {
      return bodyRejectedResponse(error, resolved.requestId);
    }

    return problemResponse({
      status: 500,
      code: "internal_error",
      requestId: resolved?.requestId ?? crypto.randomUUID()
    });
  }
}

/** A cookie-authenticated mutation with no body (cancel, withdraw). */
export async function handleReviewerEmpty<TIds extends string, TData>(
  request: Request,
  params: Promise<Readonly<Record<TIds, string>>>,
  call: (
    api: ServerApi,
    ids: Readonly<Record<TIds, string>>,
    options: ReviewerOptions
  ) => Promise<ApiResult<TData>>
): Promise<Response> {
  let resolved: Resolved | undefined;

  try {
    resolved = resolve(request);
    const current = resolved;
    const guard = guardMutation(request, {
      policy: originPolicyFor(request),
      requestId: current.requestId,
      body: { rule: "empty", maxBytes: 0 },
      afterOrigin: () => (current.session === undefined ? unauthenticated(current) : undefined),
      csrf: { presented: current.csrf, expected: current.csrf }
    });

    if (!guard.ok) {
      return guard.response;
    }

    const ids = await parseIds(params);

    if (ids === undefined || current.session === undefined) {
      return notFound(current.requestId);
    }

    return reviewerResultResponse(
      await call(serverApi(), ids, reviewerOptions(request, current, current.session, true)),
      current.names
    );
  } catch {
    return problemResponse({
      status: 500,
      code: "internal_error",
      requestId: resolved?.requestId ?? crypto.randomUUID()
    });
  }
}

/** A cookie-authenticated read: no Origin or CSRF (it changes nothing); the session is required. */
export async function handleReviewerGet<TIds extends string, TData>(
  request: Request,
  params: Promise<Readonly<Record<TIds, string>>>,
  call: (
    api: ServerApi,
    ids: Readonly<Record<TIds, string>>,
    options: ReviewerOptions
  ) => Promise<ApiResult<TData>>
): Promise<Response> {
  let resolved: Resolved | undefined;

  try {
    resolved = resolve(request);

    if (resolved.session === undefined) {
      return unauthenticated(resolved);
    }

    const ids = await parseIds(params);

    if (ids === undefined) {
      return notFound(resolved.requestId);
    }

    return reviewerResultResponse(
      await call(serverApi(), ids, reviewerOptions(request, resolved, resolved.session, false)),
      resolved.names
    );
  } catch {
    return problemResponse({
      status: 500,
      code: "internal_error",
      requestId: resolved?.requestId ?? crypto.randomUUID()
    });
  }
}

const EVIDENCE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "application/pdf"]);
const SCAN_STATES = new Set(["clean", "not_scanned_demo"]);
const FILENAME_DISPOSITION_PATTERN = /^attachment; filename="[^"\\\r\n]{1,200}"$/;

/**
 * Builds the download response from an explicit header allowlist. The API's own security headers
 * are re-asserted rather than trusted through: attachment disposition, `nosniff`, a sandboxing CSP,
 * and `no-store`. No signed URL exists; the bytes are streamed through this response only.
 */
export function evidenceResponse(evidence: EvidenceStream, requestId: string): Response {
  const headers = noStoreHeaders(requestId);
  const type = evidence.headers.get("Content-Type")?.split(";")[0]?.trim().toLowerCase() ?? "";
  const disposition = evidence.headers.get("Content-Disposition") ?? "";
  const scanState = evidence.headers.get("X-Evidence-Scan-State") ?? "";

  headers.set("Content-Type", EVIDENCE_TYPES.has(type) ? type : "application/octet-stream");
  headers.set(
    "Content-Disposition",
    disposition === "attachment" || FILENAME_DISPOSITION_PATTERN.test(disposition)
      ? disposition
      : "attachment"
  );
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Content-Security-Policy", "default-src 'none'; sandbox");

  if (SCAN_STATES.has(scanState)) {
    headers.set("X-Evidence-Scan-State", scanState);
  }

  return new Response(evidence.body, { status: 200, headers });
}

export async function handleEvidenceDownload(
  request: Request,
  params: Promise<{ readonly reportId: string; readonly evidenceId: string }>
): Promise<Response> {
  let resolved: Resolved | undefined;

  try {
    resolved = resolve(request);

    if (resolved.session === undefined) {
      return unauthenticated(resolved);
    }

    const ids = await parseIds(params);

    if (ids === undefined) {
      return notFound(resolved.requestId);
    }

    const result = await serverApi().downloadEvidence(
      ids.reportId,
      ids.evidenceId,
      reviewerOptions(request, resolved, resolved.session, false)
    );

    return result.kind === "ok"
      ? evidenceResponse(result.data, result.requestId)
      : reviewerResultResponse(result, resolved.names);
  } catch {
    return problemResponse({
      status: 500,
      code: "internal_error",
      requestId: resolved?.requestId ?? crypto.randomUUID()
    });
  }
}
