import "server-only";

import type { z } from "zod";

import type { ApiResult, MutationOptions, ServerApi } from "@/lib/api/server";
import { serverApi } from "@/lib/api/server";
import { loadPublicEnvironment } from "@/lib/config/public";
import { loadServerEnvironment } from "@/lib/config/server";
import { BodyRejectedError, limitBodyStream, readBoundedJson } from "@/lib/bff/body";
import { guardMutation } from "@/lib/bff/guard";
import { resolveOriginPolicy, type OriginPolicy } from "@/lib/bff/origin";
import {
  abortedResponse,
  apiProblemResponse,
  bodyRejectedResponse,
  noStoreHeaders,
  problemResponse,
  unavailableResponse
} from "@/lib/bff/problem";
import { forwardedContextFor } from "@/lib/bff/request-context";

/**
 * Shared plumbing for the purpose-built public handlers. It is deliberately not a proxy: every
 * caller supplies a fixed input schema, a body cap, and a closure that invokes exactly one typed
 * operation. The browser never chooses a path, method, query, or header. Nothing here reads,
 * caches, or logs a body: private values exist only in the stream/parse call stack.
 */

export const MAX_REPORT_FILE_BYTES = 10 * 1024 * 1024;
export const REPORT_MULTIPART_MAX_BYTES = 3 * MAX_REPORT_FILE_BYTES + 64 * 1024;

export type PublicJsonSpec<TInput, TData> = {
  readonly schema: z.ZodType<TInput>;
  readonly maxBodyBytes: number;
  /** True when the operation requires a validated `Idempotency-Key` from the browser. */
  readonly idempotent: boolean;
  readonly call: (
    api: ServerApi,
    input: TInput,
    options: MutationOptions
  ) => Promise<ApiResult<TData>>;
};

export function originPolicyFor(request: Request): OriginPolicy {
  return resolveOriginPolicy({
    appEnvironment: loadServerEnvironment().appEnvironment,
    publicOrigin: loadPublicEnvironment().appOrigin,
    requestUrl: request.url,
    requestHost: request.headers.get("Host")
  });
}

function validationResponse(error: z.ZodError, requestId: string): Response {
  // Only the path and Zod's rule code are reported; a submitted value never appears.
  return problemResponse({
    status: 422,
    code: "validation_failed",
    requestId,
    fieldErrors: error.issues.map((issue) => ({
      field: ["body", ...issue.path.map(String)].join("."),
      code: issue.code
    }))
  });
}

export function successResponse<TData>(
  result: Extract<ApiResult<TData>, { kind: "ok" }>
): Response {
  const headers = noStoreHeaders(result.requestId);

  if (result.replayed) {
    headers.set("Idempotency-Replayed", "true");
  }

  if (result.status === 204) {
    return new Response(null, { status: 204, headers });
  }

  headers.set("Content-Type", "application/json");

  return new Response(JSON.stringify(result.data), { status: result.status, headers });
}

export function resultResponse<TData>(result: ApiResult<TData>): Response {
  switch (result.kind) {
    case "ok":
      return successResponse(result);
    case "problem":
      return apiProblemResponse(result.problem);
    case "unavailable":
      return unavailableResponse(result.reason, result.requestId);
    case "not_modified":
      // A mutation can never be conditional; a 304 here is a contract violation, not a result.
      return problemResponse({
        status: 503,
        code: "dependency_unavailable",
        requestId: result.requestId
      });
  }
}

/** Last-resort boundary: a thrown error becomes a generic 500 with no message, stack, or cause. */
function internalErrorResponse(requestId: string): Response {
  return problemResponse({ status: 500, code: "internal_error", requestId });
}

export async function handlePublicJson<TInput, TData>(
  request: Request,
  spec: PublicJsonSpec<TInput, TData>
): Promise<Response> {
  const requestId = crypto.randomUUID();

  try {
    const guard = guardMutation(request, {
      policy: originPolicyFor(request),
      requestId,
      body: { rule: "json", maxBytes: spec.maxBodyBytes },
      requireIdempotencyKey: spec.idempotent
    });

    if (!guard.ok) {
      return guard.response;
    }

    const input = spec.schema.safeParse(await readBoundedJson(request, spec.maxBodyBytes));

    if (!input.success) {
      return validationResponse(input.error, requestId);
    }

    return resultResponse(
      await spec.call(serverApi(), input.data, {
        context: forwardedContextFor(request, requestId),
        signal: request.signal,
        idempotencyKey: guard.idempotencyKey
      })
    );
  } catch (error) {
    if (error instanceof BodyRejectedError) {
      return bodyRejectedResponse(error, requestId);
    }

    return internalErrorResponse(requestId);
  }
}

/** For operations with no request body, such as creating a reporter handle. */
export async function handlePublicEmpty<TData>(
  request: Request,
  spec: {
    readonly idempotent: boolean;
    readonly call: (api: ServerApi, options: MutationOptions) => Promise<ApiResult<TData>>;
  }
): Promise<Response> {
  const requestId = crypto.randomUUID();

  try {
    const guard = guardMutation(request, {
      policy: originPolicyFor(request),
      requestId,
      body: { rule: "empty", maxBytes: 0 },
      requireIdempotencyKey: spec.idempotent
    });

    if (!guard.ok) {
      return guard.response;
    }

    return resultResponse(
      await spec.call(serverApi(), {
        context: forwardedContextFor(request, requestId),
        signal: request.signal,
        idempotencyKey: guard.idempotencyKey
      })
    );
  } catch {
    return internalErrorResponse(requestId);
  }
}

/** Streams a capped multipart report to the API without buffering or parsing files. */
export async function handleReportSubmission(request: Request): Promise<Response> {
  const requestId = crypto.randomUUID();

  try {
    const guard = guardMutation(request, {
      policy: originPolicyFor(request),
      requestId,
      body: { rule: "multipart", maxBytes: REPORT_MULTIPART_MAX_BYTES },
      requireIdempotencyKey: true
    });

    if (!guard.ok) {
      return guard.response;
    }

    const contentType = request.headers.get("Content-Type");

    if (request.body === null || contentType === null) {
      return problemResponse({ status: 400, code: "bad_request", requestId });
    }

    let exceeded = false;
    const result = await serverApi().submitReport(
      limitBodyStream(request.body, REPORT_MULTIPART_MAX_BYTES, () => {
        exceeded = true;
      }),
      contentType,
      {
        context: forwardedContextFor(request, requestId),
        signal: request.signal,
        idempotencyKey: guard.idempotencyKey
      }
    );

    if (exceeded) {
      return bodyRejectedResponse(new BodyRejectedError("payload_too_large"), requestId);
    }

    if (result.kind === "unavailable" && result.reason === "aborted") {
      return abortedResponse(requestId);
    }

    return resultResponse(result);
  } catch {
    return internalErrorResponse(requestId);
  }
}
