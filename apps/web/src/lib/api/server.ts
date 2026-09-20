import "server-only";

import { z } from "zod";

import {
  buildForwardedHeaders,
  toEntityTag,
  type ForwardedContext
} from "@/lib/api/forwarded-context";
import { createGeneratedClient } from "@/lib/api/generated/client";
import type { components, operations } from "@/lib/api/generated/schema";
import { loadServerEnvironment, type ServerEnvironment } from "@/lib/config/server";

/**
 * Server-only transport to the private FastAPI service. It adds the internal bearer credential,
 * forwards only validated context, bounds every call with a timeout, and returns a typed result
 * instead of throwing or echoing backend detail. It performs no logging by design: request bodies,
 * credentials, cookies, and private content must never reach a log line from this module.
 */

const INTERNAL_CALLER_ID = "web";
const PUBLIC_READ_TIMEOUT_MS = 5_000;
const PUBLIC_REVALIDATE_SECONDS = 60;
const READ_RETRY_DELAY_MS = 250;
const MAX_RETRY_AFTER_FOR_RETRY_SECONDS = 1;

const problemSchema = z.object({
  code: z.string().min(1).max(100),
  title: z.string().max(300),
  status: z.number().int(),
  request_id: z.string().nullish(),
  errors: z.array(z.object({ field: z.string().max(300), code: z.string().max(100) })).nullish()
});

export type ApiProblem = {
  readonly status: number;
  readonly code: string;
  readonly requestId: string;
  readonly fieldErrors: readonly { readonly field: string; readonly code: string }[];
  readonly retryAfterSeconds: number | undefined;
};

export type ApiUnavailableReason = "timeout" | "network" | "malformed_response";

export type ApiResult<TData> =
  | {
      readonly kind: "ok";
      readonly data: TData;
      readonly etag: string | undefined;
      readonly requestId: string;
    }
  | { readonly kind: "not_modified"; readonly etag: string | undefined; readonly requestId: string }
  | { readonly kind: "problem"; readonly problem: ApiProblem }
  | {
      readonly kind: "unavailable";
      readonly reason: ApiUnavailableReason;
      readonly requestId: string;
    };

export type ReadContext = ForwardedContext & {
  /** Previous `ETag`; a matching public read answers `not_modified`. */
  readonly ifNoneMatch?: unknown;
};

type RawResult<TData> = {
  readonly data?: TData | undefined;
  readonly error?: unknown;
  readonly response: Response;
};

type SendInit = {
  readonly headers: Record<string, string>;
  readonly fetch: (request: Request) => Promise<Response>;
  readonly signal: AbortSignal;
};

export type ServerApiDependencies = {
  readonly environment: ServerEnvironment;
  readonly fetch: typeof fetch;
  readonly sleep: (milliseconds: number) => Promise<void>;
  readonly generateRequestId: () => string;
};

function parseRetryAfter(response: Response): number | undefined {
  const value = response.headers.get("Retry-After");

  if (value === null || !/^\d{1,6}$/.test(value)) {
    return undefined;
  }

  return Number(value);
}

function toProblem(raw: RawResult<unknown>, requestId: string): ApiProblem | undefined {
  const parsed = problemSchema.safeParse(raw.error);

  if (!parsed.success) {
    return undefined;
  }

  return {
    status: raw.response.status,
    code: parsed.data.code,
    // The request ID we sent is authoritative; a backend-supplied one is only a fallback.
    requestId: requestId,
    fieldErrors: (parsed.data.errors ?? []).map(({ field, code }) => ({ field, code })),
    retryAfterSeconds: parseRetryAfter(raw.response)
  };
}

function isTransient(raw: RawResult<unknown>): boolean {
  if (raw.response.status !== 503) {
    return false;
  }

  const retryAfter = parseRetryAfter(raw.response);

  return retryAfter === undefined || retryAfter <= MAX_RETRY_AFTER_FOR_RETRY_SECONDS;
}

function isAbortError(error: unknown): boolean {
  return (
    error instanceof DOMException && (error.name === "TimeoutError" || error.name === "AbortError")
  );
}

export function createServerApi(dependencies: ServerApiDependencies) {
  const baseUrl = dependencies.environment.apiInternalUrl;
  const authorization = `Bearer ${INTERNAL_CALLER_ID}.${dependencies.environment.internalWebCredential}`;

  /**
   * Reads are retried once, and only for a transient 503 or a network failure. A timeout is not
   * retried (it already consumed the operation's budget) and mutations never go through here.
   */
  async function read<TData>(
    send: (init: SendInit) => Promise<RawResult<TData>>,
    context: ReadContext
  ): Promise<ApiResult<TData>> {
    const { headers, requestId } = buildForwardedHeaders(context, dependencies.generateRequestId);
    const etag = toEntityTag(context.ifNoneMatch);
    const requestHeaders: Record<string, string> = {
      ...headers,
      Authorization: authorization,
      Accept: "application/json, application/problem+json"
    };

    if (etag !== undefined) {
      requestHeaders["If-None-Match"] = etag;
    }

    const cachedFetch = (request: Request): Promise<Response> =>
      dependencies.fetch(request, {
        next: { revalidate: PUBLIC_REVALIDATE_SECONDS }
      } as RequestInit);

    for (let attempt = 0; attempt < 2; attempt += 1) {
      let raw: RawResult<TData>;

      try {
        raw = await send({
          headers: requestHeaders,
          fetch: cachedFetch,
          signal: AbortSignal.timeout(PUBLIC_READ_TIMEOUT_MS)
        });
      } catch (error) {
        if (isAbortError(error)) {
          return { kind: "unavailable", reason: "timeout", requestId };
        }

        if (error instanceof SyntaxError) {
          return { kind: "unavailable", reason: "malformed_response", requestId };
        }

        if (attempt === 0) {
          await dependencies.sleep(READ_RETRY_DELAY_MS);
          continue;
        }

        return { kind: "unavailable", reason: "network", requestId };
      }

      const responseEtag = toEntityTag(raw.response.headers.get("ETag"));

      if (raw.response.status === 304) {
        return { kind: "not_modified", etag: responseEtag ?? etag, requestId };
      }

      if (raw.response.ok && raw.data !== undefined) {
        return { kind: "ok", data: raw.data, etag: responseEtag, requestId };
      }

      if (attempt === 0 && isTransient(raw)) {
        await dependencies.sleep(READ_RETRY_DELAY_MS);
        continue;
      }

      const problem = raw.response.ok ? undefined : toProblem(raw, requestId);

      return problem === undefined
        ? { kind: "unavailable", reason: "malformed_response", requestId }
        : { kind: "problem", problem };
    }

    return { kind: "unavailable", reason: "network", requestId };
  }

  const client = createGeneratedClient(baseUrl);

  return {
    getLocalities: (context: ReadContext = {}) =>
      read<components["schemas"]["LocalityListOut"]>(
        (init) => client.GET("/v1/localities", init),
        context
      ),

    listProjects: (
      query: NonNullable<operations["projects_list"]["parameters"]["query"]>,
      context: ReadContext = {}
    ) =>
      read<components["schemas"]["ProjectPageOut"]>(
        (init) => client.GET("/v1/projects", { ...init, params: { query } }),
        context
      ),

    getProject: (slug: string, context: ReadContext = {}) =>
      read<components["schemas"]["ProjectDetailOut"]>(
        (init) => client.GET("/v1/projects/{slug}", { ...init, params: { path: { slug } } }),
        context
      ),

    getProjectSource: (slug: string, sourceId: string, context: ReadContext = {}) =>
      read<components["schemas"]["SourceExcerptsOut"]>(
        (init) =>
          client.GET("/v1/projects/{slug}/sources/{source_id}", {
            ...init,
            params: { path: { slug, source_id: sourceId } }
          }),
        context
      )
  };
}

export type ServerApi = ReturnType<typeof createServerApi>;

/** Builds the client from runtime configuration on first use, never at import or build time. */
export function serverApi(): ServerApi {
  return createServerApi({
    environment: loadServerEnvironment(),
    fetch: (input, init) => globalThis.fetch(input, init),
    sleep: (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)),
    generateRequestId: () => crypto.randomUUID()
  });
}
