import "server-only";

import { z } from "zod";

import {
  buildForwardedHeaders,
  toEntityTag,
  toOpaqueSecret,
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

/** Every cached public read carries this tag so one call can drop all of them after a publication. */
export const PUBLIC_CACHE_TAG = "public-catalogue";
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

export type ApiUnavailableReason = "timeout" | "network" | "malformed_response" | "aborted";

export type ApiResult<TData> =
  | {
      readonly kind: "ok";
      readonly status: number;
      readonly data: TData;
      readonly etag: string | undefined;
      /** True when the API replayed an earlier identical idempotent request. */
      readonly replayed: boolean;
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

function abortKind(error: unknown): "timeout" | "aborted" | undefined {
  if (!(error instanceof DOMException)) {
    return undefined;
  }

  // `AbortSignal.any` rethrows the reason of whichever signal fired first: a TimeoutError for our
  // deadline, an AbortError when the caller (a disconnected browser) cancelled.
  return error.name === "TimeoutError"
    ? "timeout"
    : error.name === "AbortError"
      ? "aborted"
      : undefined;
}

type CallPolicy = {
  readonly context: ReadContext;
  readonly timeoutMs: number;
  /** Reads may retry once; a mutation is never retried automatically. */
  readonly retry: boolean;
  readonly cache: "public" | "no-store";
  /** Cancels the call when the browser disconnects. */
  readonly signal?: AbortSignal | undefined;
  /** Already-validated extra headers, such as `Idempotency-Key`. */
  readonly headers?: Readonly<Record<string, string>> | undefined;
};

export type MutationOptions = {
  readonly context: ForwardedContext;
  readonly signal?: AbortSignal | undefined;
  readonly idempotencyKey?: string | undefined;
};

/** Reviewer calls carry the session (and, for mutations, CSRF) token resolved from HttpOnly cookies. */
export type ReviewerOptions = {
  readonly context: ForwardedContext;
  readonly signal?: AbortSignal | undefined;
  readonly session: string;
  readonly csrf?: string | undefined;
};

export type EvidenceStream = {
  readonly body: ReadableStream<Uint8Array>;
  readonly headers: Headers;
};

// Transport budgets from the BFF operation map (connect is folded into the total).
const PUBLIC_JSON_TIMEOUT_MS = 8_000;
const PUBLIC_POLL_TIMEOUT_MS = 3_000;
const REPORT_SUBMIT_TIMEOUT_MS = 65_000;
const REVIEWER_READ_TIMEOUT_MS = 5_000;
const REVIEWER_MUTATION_TIMEOUT_MS = 10_000;
const REVIEWER_POLL_TIMEOUT_MS = 3_000;
const AUTH_TIMEOUT_MS = 8_000;
const EVIDENCE_STREAM_TIMEOUT_MS = 30_000;

export function createServerApi(dependencies: ServerApiDependencies) {
  const baseUrl = dependencies.environment.apiInternalUrl;
  const authorization = `Bearer ${INTERNAL_CALLER_ID}.${dependencies.environment.internalWebCredential}`;

  /**
   * Every call goes through here. Reads may retry once, and only for a transient 503 or a network
   * failure. Mutations never retry: a network error after sending means completion is unknown, and
   * the caller must reuse the same idempotency key or refetch state.
   */
  async function execute<TData>(
    send: (init: SendInit) => Promise<RawResult<TData>>,
    policy: CallPolicy
  ): Promise<ApiResult<TData>> {
    const { headers, requestId } = buildForwardedHeaders(
      policy.context,
      dependencies.generateRequestId
    );
    const etag = toEntityTag(policy.context.ifNoneMatch);
    const requestHeaders: Record<string, string> = {
      ...policy.headers,
      ...headers,
      Authorization: authorization,
      Accept: "application/json, application/problem+json"
    };

    if (etag !== undefined) {
      requestHeaders["If-None-Match"] = etag;
    }

    const cachedFetch = (request: Request): Promise<Response> =>
      dependencies.fetch(
        request,
        (policy.cache === "public"
          ? { next: { revalidate: PUBLIC_REVALIDATE_SECONDS, tags: [PUBLIC_CACHE_TAG] } }
          : { cache: "no-store" }) as RequestInit
      );
    const attempts = policy.retry ? 2 : 1;

    for (let attempt = 0; attempt < attempts; attempt += 1) {
      const deadline = AbortSignal.timeout(policy.timeoutMs);
      let raw: RawResult<TData>;

      try {
        raw = await send({
          headers: requestHeaders,
          fetch: cachedFetch,
          signal:
            policy.signal === undefined ? deadline : AbortSignal.any([policy.signal, deadline])
        });
      } catch (error) {
        const aborted = abortKind(error);

        if (aborted !== undefined) {
          return { kind: "unavailable", reason: aborted, requestId };
        }

        if (error instanceof SyntaxError) {
          return { kind: "unavailable", reason: "malformed_response", requestId };
        }

        if (attempt + 1 < attempts) {
          await dependencies.sleep(READ_RETRY_DELAY_MS);
          continue;
        }

        return { kind: "unavailable", reason: "network", requestId };
      }

      const responseEtag = toEntityTag(raw.response.headers.get("ETag"));

      if (raw.response.status === 304) {
        return { kind: "not_modified", etag: responseEtag ?? etag, requestId };
      }

      if (raw.response.ok && (raw.data !== undefined || raw.response.status === 204)) {
        return {
          kind: "ok",
          status: raw.response.status,
          // A 204 has no body; its operations are typed as `undefined` data.
          data: raw.data as TData,
          etag: responseEtag,
          replayed: raw.response.headers.get("Idempotency-Replayed") === "true",
          requestId
        };
      }

      if (attempt + 1 < attempts && isTransient(raw)) {
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

  const read = <TData>(
    send: (init: SendInit) => Promise<RawResult<TData>>,
    context: ReadContext
  ): Promise<ApiResult<TData>> =>
    execute(send, {
      context,
      timeoutMs: PUBLIC_READ_TIMEOUT_MS,
      retry: true,
      cache: "public"
    });

  const mutate = <TData>(
    send: (init: SendInit) => Promise<RawResult<TData>>,
    options: MutationOptions,
    timeoutMs: number = PUBLIC_JSON_TIMEOUT_MS
  ): Promise<ApiResult<TData>> =>
    execute(send, {
      context: options.context,
      timeoutMs,
      retry: false,
      cache: "no-store",
      signal: options.signal,
      headers:
        options.idempotencyKey === undefined
          ? undefined
          : { "Idempotency-Key": options.idempotencyKey }
    });

  function reviewerHeaders(options: ReviewerOptions): Record<string, string> {
    const session = toOpaqueSecret(options.session);
    const csrf = toOpaqueSecret(options.csrf);
    const headers: Record<string, string> = {};

    if (session !== undefined) {
      headers["X-Shaidago-Session"] = session;
    }

    if (csrf !== undefined) {
      headers["X-Shaidago-Csrf"] = csrf;
    }

    return headers;
  }

  const reviewerCall = <TData>(
    send: (init: SendInit) => Promise<RawResult<TData>>,
    options: ReviewerOptions,
    policy: { readonly timeoutMs: number; readonly retry: boolean }
  ): Promise<ApiResult<TData>> =>
    execute(send, {
      context: options.context,
      timeoutMs: policy.timeoutMs,
      retry: policy.retry,
      cache: "no-store",
      signal: options.signal,
      headers: reviewerHeaders(options)
    });

  const reviewerRead = <TData>(
    send: (init: SendInit) => Promise<RawResult<TData>>,
    options: ReviewerOptions,
    timeoutMs: number = REVIEWER_READ_TIMEOUT_MS
  ) => reviewerCall(send, options, { timeoutMs, retry: true });

  const reviewerMutate = <TData>(
    send: (init: SendInit) => Promise<RawResult<TData>>,
    options: ReviewerOptions
  ) => reviewerCall(send, options, { timeoutMs: REVIEWER_MUTATION_TIMEOUT_MS, retry: false });

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
      ),

    // Public mutations and polling. Each names exactly one operation; none accepts a path, method,
    // or header chosen by the browser.
    askQuestion: (
      slug: string,
      body: components["schemas"]["ProjectQuestionIn"],
      options: MutationOptions
    ) =>
      mutate<components["schemas"]["ProjectQuestionOut"]>(
        (init) =>
          client.POST("/v1/projects/{slug}/questions", {
            ...init,
            params: { path: { slug } },
            body
          }),
        options
      ),

    startPublicDiscovery: (slug: string, options: MutationOptions) =>
      mutate<components["schemas"]["RunStartedOut"]>(
        (init) =>
          client.POST("/v1/projects/{slug}/discovery-runs", {
            ...init,
            params: { path: { slug } }
          }),
        options
      ),

    getPublicDiscoveryRun: (
      runId: string,
      sinceVersion: number | undefined,
      options: MutationOptions
    ) =>
      execute<components["schemas"]["RunOut"]>(
        (init) =>
          client.GET("/v1/discovery-runs/{run_id}", {
            ...init,
            params: {
              path: { run_id: runId },
              query: sinceVersion === undefined ? {} : { since_version: sinceVersion }
            }
          }),
        {
          context: options.context,
          timeoutMs: PUBLIC_POLL_TIMEOUT_MS,
          retry: false,
          cache: "no-store",
          signal: options.signal
        }
      ),

    /** Streams the browser's multipart body; the caller has already capped it and set the boundary. */
    submitReport: (
      body: ReadableStream<Uint8Array>,
      multipartContentType: string,
      options: MutationOptions
    ) =>
      mutate<components["schemas"]["ReportReceipt"]>(
        (init) =>
          client.POST("/v1/reports", {
            ...init,
            headers: { ...init.headers, "Content-Type": multipartContentType },
            // The generated multipart type describes parsed fields; the stream is forwarded as-is.
            body: body as unknown as never,
            bodySerializer: (value: unknown) => value as BodyInit,
            duplex: "half"
          } as never),
        options,
        REPORT_SUBMIT_TIMEOUT_MS
      ),

    lookupReportStatus: (
      body: components["schemas"]["StatusLookupRequest"],
      options: MutationOptions
    ) =>
      mutate<components["schemas"]["ReportStatusOut"]>(
        (init) => client.POST("/v1/report-status:lookup", { ...init, body }),
        options
      ),

    answerFollowUp: (body: components["schemas"]["AnswerRequest"], options: MutationOptions) =>
      mutate<components["schemas"]["AnswerAck"]>(
        (init) => client.POST("/v1/report-status:answer-follow-up", { ...init, body }),
        options
      ),

    createReporterHandle: (options: MutationOptions) =>
      mutate<components["schemas"]["HandleCreated"]>(
        (init) => client.POST("/v1/reporter-handles", init),
        options
      ),

    listHandleReports: (body: components["schemas"]["Credentials"], options: MutationOptions) =>
      mutate<components["schemas"]["HandleReports"]>(
        (init) => client.POST("/v1/reporter-handles:list-reports", { ...init, body }),
        options
      ),

    deleteReporterHandle: (body: components["schemas"]["Credentials"], options: MutationOptions) =>
      mutate<undefined>(
        (init) => client.POST("/v1/reporter-handles:delete", { ...init, body }),
        options
      ),

    // Reviewer authentication. The one-time session response never leaves server execution.
    signIn: (body: components["schemas"]["SignInRequest"], options: MutationOptions) =>
      mutate<components["schemas"]["SessionOut"]>(
        (init) => client.POST("/v1/auth/sessions", { ...init, body }),
        options,
        AUTH_TIMEOUT_MS
      ),

    signOut: (options: ReviewerOptions) =>
      reviewerCall<undefined>((init) => client.DELETE("/v1/auth/sessions/current", init), options, {
        timeoutMs: AUTH_TIMEOUT_MS,
        retry: false
      }),

    // Reviewer reads (SR-REVIEWER / BFF-REVIEWER-GET): session forwarded, never cached.
    listReviewerReports: (
      query: NonNullable<operations["reviewer_reports_queue"]["parameters"]["query"]>,
      options: ReviewerOptions
    ) =>
      reviewerRead<components["schemas"]["QueuePageOut"]>(
        (init) => client.GET("/v1/reviewer/reports", { ...init, params: { query } }),
        options
      ),

    getReviewerReport: (reportId: string, includeContact: boolean, options: ReviewerOptions) =>
      reviewerRead<components["schemas"]["ReportDetailOut"]>(
        (init) =>
          client.GET("/v1/reviewer/reports/{report_id}", {
            ...init,
            params: { path: { report_id: reportId }, query: { include_contact: includeContact } }
          }),
        options
      ),

    listReviewerNotes: (
      reportId: string,
      query: NonNullable<operations["reviewer_notes_list"]["parameters"]["query"]>,
      options: ReviewerOptions
    ) =>
      reviewerRead<components["schemas"]["NotePageOut"]>(
        (init) =>
          client.GET("/v1/reviewer/reports/{report_id}/notes", {
            ...init,
            params: { path: { report_id: reportId }, query }
          }),
        options
      ),

    listPublicationDrafts: (reportId: string, options: ReviewerOptions) =>
      reviewerRead<components["schemas"]["DraftListOut"]>(
        (init) =>
          client.GET("/v1/reviewer/reports/{report_id}/public-updates", {
            ...init,
            params: { path: { report_id: reportId } }
          }),
        options
      ),

    getPublicationPreview: (reportId: string, updateId: string, options: ReviewerOptions) =>
      reviewerRead<components["schemas"]["PreviewOut"]>(
        (init) =>
          client.GET("/v1/reviewer/reports/{report_id}/public-updates/{update_id}", {
            ...init,
            params: { path: { report_id: reportId, update_id: updateId } }
          }),
        options
      ),

    getReviewerDiscoveryRun: (runId: string, options: ReviewerOptions) =>
      reviewerRead<components["schemas"]["ReviewerRunOut"]>(
        (init) =>
          client.GET("/v1/reviewer/discovery-runs/{run_id}", {
            ...init,
            params: { path: { run_id: runId } }
          }),
        options,
        REVIEWER_POLL_TIMEOUT_MS
      ),

    /** Streams one sanitised attachment; the caller decides which backend headers to expose. */
    downloadEvidence: (reportId: string, evidenceId: string, options: ReviewerOptions) =>
      reviewerCall<EvidenceStream>(
        async (init) => {
          const raw = await client.GET(
            "/v1/reviewer/reports/{report_id}/evidence/{evidence_id}/content",
            {
              ...init,
              params: { path: { report_id: reportId, evidence_id: evidenceId } },
              parseAs: "stream"
            }
          );

          return {
            data:
              raw.data === undefined || raw.data === null
                ? undefined
                : { body: raw.data, headers: raw.response.headers },
            error: raw.error,
            response: raw.response
          };
        },
        options,
        { timeoutMs: EVIDENCE_STREAM_TIMEOUT_MS, retry: false }
      ),

    // Reviewer mutations: Origin/CSRF are enforced by the BFF first; the API re-checks the token.
    createNote: (
      reportId: string,
      body: components["schemas"]["NoteRequest"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["NoteCreatedOut"]>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/notes", {
            ...init,
            params: { path: { report_id: reportId } },
            body
          }),
        options
      ),

    askReviewerFollowUp: (
      reportId: string,
      body: components["schemas"]["QuestionRequest"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["QuestionOut"]>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/follow-up-questions", {
            ...init,
            params: { path: { report_id: reportId } },
            body
          }),
        options
      ),

    withdrawReviewerFollowUp: (reportId: string, questionId: string, options: ReviewerOptions) =>
      reviewerMutate<undefined>(
        (init) =>
          client.POST(
            "/v1/reviewer/reports/{report_id}/follow-up-questions/{question_id}:withdraw",
            { ...init, params: { path: { report_id: reportId, question_id: questionId } } }
          ),
        options
      ),

    transitionReport: (
      reportId: string,
      body: components["schemas"]["TransitionRequest"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["TransitionOut"]>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/status-transitions", {
            ...init,
            params: { path: { report_id: reportId } },
            body
          }),
        options
      ),

    createPublicationDraft: (
      reportId: string,
      body: components["schemas"]["DraftIn"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["PreviewOut"]>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/public-updates", {
            ...init,
            params: { path: { report_id: reportId } },
            body
          }),
        options
      ),

    publishUpdate: (
      reportId: string,
      updateId: string,
      body: components["schemas"]["PublishIn"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["PublishedOut"]>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/public-updates/{update_id}:publish", {
            ...init,
            params: { path: { report_id: reportId, update_id: updateId } },
            body
          }),
        options
      ),

    withdrawUpdate: (reportId: string, updateId: string, options: ReviewerOptions) =>
      reviewerMutate<undefined>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/public-updates/{update_id}:withdraw", {
            ...init,
            params: { path: { report_id: reportId, update_id: updateId } }
          }),
        options
      ),

    planDiscovery: (
      reportId: string,
      body: components["schemas"]["PlanIn"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["PlanOut"]>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/discovery-runs:plan", {
            ...init,
            params: { path: { report_id: reportId } },
            body
          }),
        options
      ),

    createDiscoveryRun: (
      reportId: string,
      body: components["schemas"]["RunCreateIn"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["RunCreatedOut"]>(
        (init) =>
          client.POST("/v1/reviewer/reports/{report_id}/discovery-runs", {
            ...init,
            params: { path: { report_id: reportId } },
            body
          }),
        options
      ),

    cancelDiscoveryRun: (runId: string, options: ReviewerOptions) =>
      reviewerMutate<components["schemas"]["CancelOut"]>(
        (init) =>
          client.POST("/v1/reviewer/discovery-runs/{run_id}:cancel", {
            ...init,
            params: { path: { run_id: runId } }
          }),
        options
      ),

    reviewDiscoveryRun: (
      runId: string,
      body: components["schemas"]["ReviewIn"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["ReviewOut"]>(
        (init) =>
          client.POST("/v1/reviewer/discovery-runs/{run_id}:review", {
            ...init,
            params: { path: { run_id: runId } },
            body
          }),
        options
      ),

    answerDiscoveryFollowUp: (
      runId: string,
      body: components["schemas"]["AnswerIn"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<undefined>(
        (init) =>
          client.POST("/v1/reviewer/discovery-runs/{run_id}/follow-up-answers", {
            ...init,
            params: { path: { run_id: runId } },
            body
          }),
        options
      ),

    decideDiscoveredSource: (
      sourceId: string,
      body: components["schemas"]["DecisionIn"],
      options: ReviewerOptions
    ) =>
      reviewerMutate<components["schemas"]["DecisionOut"]>(
        (init) =>
          client.POST("/v1/reviewer/discovered-sources/{source_id}/decision", {
            ...init,
            params: { path: { source_id: sourceId } },
            body
          }),
        options
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
