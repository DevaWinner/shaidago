import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { DELETE as signOut, POST as signIn } from "../../app/api/reviewer/session/route";
import { POST as createNote } from "../../app/api/reviewer/reports/[reportId]/notes/route";
import { GET as downloadEvidence } from "../../app/api/reviewer/reports/[reportId]/evidence/[evidenceId]/route";
import { POST as askFollowUp } from "../../app/api/reviewer/reports/[reportId]/follow-up-questions/route";
import { POST as withdrawFollowUp } from "../../app/api/reviewer/reports/[reportId]/follow-up-questions/[questionId]/withdraw/route";
import { POST as transition } from "../../app/api/reviewer/reports/[reportId]/status-transition/route";
import { POST as createDraft } from "../../app/api/reviewer/reports/[reportId]/public-updates/route";
import { GET as previewUpdate } from "../../app/api/reviewer/reports/[reportId]/public-updates/[updateId]/route";
import { POST as publishUpdate } from "../../app/api/reviewer/reports/[reportId]/public-updates/[updateId]/publish/route";
import { POST as withdrawUpdate } from "../../app/api/reviewer/reports/[reportId]/public-updates/[updateId]/withdraw/route";
import { POST as planDiscovery } from "../../app/api/reviewer/reports/[reportId]/discovery/plan/route";
import { POST as createRun } from "../../app/api/reviewer/reports/[reportId]/discovery/route";
import { GET as getRun } from "../../app/api/reviewer/discovery/[runId]/route";
import { POST as cancelRun } from "../../app/api/reviewer/discovery/[runId]/cancel/route";
import { POST as reviewRun } from "../../app/api/reviewer/discovery/[runId]/review/route";
import { POST as answerRun } from "../../app/api/reviewer/discovery/[runId]/follow-up-answers/route";
import { POST as decideSource } from "../../app/api/reviewer/discovered-sources/[sourceId]/decision/route";
import {
  buildSessionCookies,
  cookieNamesFor,
  readReviewerCookies
} from "@/lib/bff/reviewer-session";

const origin = "http://localhost:3000";
const credential = "shaida-go-unit-test-credential-not-a-secret";
const sessionToken = "session-token-value-0123456789abcdef";
const csrfToken = "csrf-token-value-0123456789abcdefghij";
const reportId = "0198f1a2-7b3c-4d4e-8f5a-123456789a01";
const otherId = "0198f1a2-7b3c-4d4e-8f5a-123456789a02";
const digest = "a".repeat(64);
const cookies = `sg_session=${sessionToken}; sg_csrf=${csrfToken}`;

const problemJson = (code: string, status: number) =>
  new Response(
    JSON.stringify({
      type: "about:blank",
      title: "t",
      status,
      code,
      detail: "secret backend detail"
    }),
    { status, headers: { "Content-Type": "application/problem+json" } }
  );
const okJson = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const sessionOut = (overrides: Record<string, unknown> = {}) => ({
  session_token: sessionToken,
  csrf_token: csrfToken,
  expires_at: "2026-09-21T10:00:00Z",
  idle_timeout_seconds: 1800,
  reviewer: { role: "reviewer" },
  cookie: {
    name: "sg_session",
    secure: false,
    http_only: true,
    same_site: "lax",
    path: "/",
    max_age_seconds: 28800,
    ...((overrides["cookie"] as object | undefined) ?? {})
  }
});

let backend: MockInstance<typeof fetch>;

beforeEach(() => {
  vi.stubEnv("APP_ENV", "test");
  vi.stubEnv("API_INTERNAL_URL", "http://api.internal-test.invalid");
  vi.stubEnv("INTERNAL_WEB_CREDENTIAL_CURRENT", credential);
  vi.stubEnv("NEXT_PUBLIC_APP_ORIGIN", undefined);
  backend = vi.spyOn(globalThis, "fetch");
});

afterEach(() => {
  vi.unstubAllEnvs();
});

function sentAt(index: number): Request {
  const request = backend.mock.calls[index]?.[0];

  if (!(request instanceof Request)) {
    throw new Error("expected a backend request");
  }

  return request;
}

function request(
  method: string,
  path: string,
  init: { body?: unknown; headers?: Record<string, string>; cookie?: string | null } = {}
): Request {
  const headers: Record<string, string> = { Origin: origin, ...init.headers };
  const cookie = init.cookie === undefined ? cookies : init.cookie;

  if (cookie !== null) {
    headers["Cookie"] = cookie;
  }

  if (init.body !== undefined) {
    headers["Content-Type"] ??= "application/json";
  }

  return new Request(`${origin}${path}`, {
    method,
    headers,
    body: init.body === undefined ? null : JSON.stringify(init.body)
  });
}

describe("reviewer sign-in", () => {
  const body = { identifier: "demo-reviewer", password: "fictional-password-value" };

  it("turns the one-time API session into HttpOnly cookies and strips tokens from the body", async () => {
    backend.mockResolvedValueOnce(okJson(sessionOut(), 201));

    const response = await signIn(request("POST", "/api/reviewer/session", { body, cookie: null }));
    const text = await response.text();
    const setCookies = response.headers.getSetCookie();

    expect(response.status).toBe(201);
    expect(JSON.parse(text)).toEqual({
      reviewer: { role: "reviewer" },
      expires_at: "2026-09-21T10:00:00Z",
      idle_timeout_seconds: 1800
    });
    expect(text).not.toContain(sessionToken);
    expect(text).not.toContain(csrfToken);
    expect(text).not.toMatch(/cookie|max_age/i);
    expect(setCookies).toHaveLength(2);
    expect(setCookies[0]).toBe(
      `sg_session=${sessionToken}; Path=/; Max-Age=28800; HttpOnly; SameSite=Lax`
    );
    expect(setCookies[1]).toContain(`sg_csrf=${csrfToken}`);
    for (const cookie of setCookies) {
      expect(cookie).toContain("HttpOnly");
    }
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(sentAt(0).headers.get("Cookie")).toBeNull();
    expect(sentAt(0).headers.get("X-Shaidago-Session")).toBeNull();
    expect(JSON.parse(await sentAt(0).text())).toEqual(body);
  });

  it("uses Secure __Host- cookies in staging and refuses a policy that disagrees", async () => {
    vi.stubEnv("APP_ENV", "staging");
    vi.stubEnv("CLIENT_HMAC_KEY", Buffer.alloc(32, 9).toString("base64"));
    vi.stubEnv("NEXT_PUBLIC_APP_ORIGIN", origin);
    backend.mockResolvedValueOnce(
      okJson(sessionOut({ cookie: { name: "__Host-sg_session", secure: true } }), 201)
    );

    const good = await signIn(request("POST", "/api/reviewer/session", { body, cookie: null }));
    expect(good.headers.getSetCookie()[0]).toBe(
      `__Host-sg_session=${sessionToken}; Path=/; Max-Age=28800; HttpOnly; SameSite=Lax; Secure`
    );

    // The API says a non-Secure plain-name cookie: the BFF refuses it and revokes the session.
    backend
      .mockResolvedValueOnce(okJson(sessionOut(), 201))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const bad = await signIn(request("POST", "/api/reviewer/session", { body, cookie: null }));
    expect(bad.status).toBe(503);
    expect(bad.headers.getSetCookie()).toEqual([]);
    expect(sentAt(2).method).toBe("DELETE");
    expect(sentAt(2).headers.get("X-Shaidago-Session")).toBe(sessionToken);
  });

  it("refuses weak or malformed cookie policies and unsafe token characters", () => {
    const names = cookieNamesFor("test");
    const base = sessionOut() as never;
    expect(() => buildSessionCookies(base, names)).not.toThrow();
    for (const cookie of [
      { http_only: false },
      { same_site: "none" },
      { path: "/reviewer" },
      { max_age_seconds: 0 },
      { max_age_seconds: 99_999_999 },
      { name: "other" },
      { secure: true }
    ]) {
      expect(
        () => buildSessionCookies(sessionOut({ cookie }) as never, names),
        JSON.stringify(cookie)
      ).toThrow();
    }
    const injected = {
      ...(sessionOut() as object),
      session_token: "abcdefghijklmnop; Domain=evil"
    };
    expect(() => buildSessionCookies(injected as never, names)).toThrow();
  });

  it("keeps invalid credentials generic and sets no cookie", async () => {
    backend.mockResolvedValueOnce(problemJson("invalid_credentials", 401));
    const response = await signIn(request("POST", "/api/reviewer/session", { body, cookie: null }));
    const text = await response.text();
    expect(response.status).toBe(401);
    expect(response.headers.getSetCookie()).toEqual([]);
    expect(JSON.parse(text)).toMatchObject({ code: "invalid_credentials" });
    expect(text).not.toContain("secret backend detail");
    expect(text).not.toContain("fictional-password-value");
  });

  it("rejects a foreign Origin, wrong type, oversize, and unknown fields before the API", async () => {
    const foreign = request("POST", "/api/reviewer/session", {
      body,
      headers: { Origin: "https://evil.example" }
    });
    expect((await signIn(foreign)).status).toBe(403);
    expect(
      (
        await signIn(
          request("POST", "/api/reviewer/session", {
            body,
            headers: { "Content-Type": "text/plain" }
          })
        )
      ).status
    ).toBe(415);
    expect(
      (
        await signIn(
          request("POST", "/api/reviewer/session", { body: { ...body, pad: "x".repeat(3000) } })
        )
      ).status
    ).toBe(413);
    const unknown = await signIn(
      request("POST", "/api/reviewer/session", { body: { ...body, extra: "leaked-value" } })
    );
    expect(unknown.status).toBe(422);
    expect(await unknown.text()).not.toContain("leaked-value");
    expect(backend).not.toHaveBeenCalled();
  });

  it("maps outages to safe problems", async () => {
    backend.mockRejectedValueOnce(new DOMException("timed out", "TimeoutError"));
    expect((await signIn(request("POST", "/api/reviewer/session", { body }))).status).toBe(504);
    backend.mockRejectedValueOnce(new TypeError("fetch failed"));
    expect((await signIn(request("POST", "/api/reviewer/session", { body }))).status).toBe(503);
    expect(backend).toHaveBeenCalledTimes(2);
  });
});

describe("reviewer sign-out", () => {
  it("revokes the API session with both tokens and clears both cookies", async () => {
    backend.mockResolvedValueOnce(new Response(null, { status: 204 }));

    const response = await signOut(request("DELETE", "/api/reviewer/session"));

    expect(response.status).toBe(204);
    const cleared = response.headers.getSetCookie();
    expect(cleared).toHaveLength(2);
    expect(
      cleared.every((cookie) => cookie.includes("Max-Age=0") && cookie.includes("HttpOnly"))
    ).toBe(true);
    expect(sentAt(0).method).toBe("DELETE");
    expect(sentAt(0).headers.get("X-Shaidago-Session")).toBe(sessionToken);
    expect(sentAt(0).headers.get("X-Shaidago-Csrf")).toBe(csrfToken);
    expect(sentAt(0).headers.get("Cookie")).toBeNull();
  });

  it("clears cookies without calling the API when there is no session", async () => {
    const response = await signOut(request("DELETE", "/api/reviewer/session", { cookie: null }));
    expect(response.status).toBe(204);
    expect(response.headers.getSetCookie()).toHaveLength(2);
    expect(backend).not.toHaveBeenCalled();
  });

  it("treats an already-gone session as signed out but still reports an outage", async () => {
    backend.mockResolvedValueOnce(problemJson("unauthenticated", 401));
    const gone = await signOut(request("DELETE", "/api/reviewer/session"));
    expect(gone.status).toBe(204);
    expect(gone.headers.getSetCookie()).toHaveLength(2);

    backend.mockRejectedValueOnce(new TypeError("down"));
    const outage = await signOut(request("DELETE", "/api/reviewer/session"));
    expect(outage.status).toBe(503);
    expect(outage.headers.getSetCookie()).toHaveLength(2);
  });

  it("requires Origin and CSRF when a session exists, and rejects a body", async () => {
    expect(
      (
        await signOut(
          request("DELETE", "/api/reviewer/session", {
            headers: { Origin: "https://evil.example" }
          })
        )
      ).status
    ).toBe(403);
    const noCsrf = await signOut(
      request("DELETE", "/api/reviewer/session", { cookie: `sg_session=${sessionToken}` })
    );
    expect(noCsrf.status).toBe(403);
    expect(((await noCsrf.json()) as { code: string }).code).toBe("csrf_invalid");
    expect(
      (await signOut(request("DELETE", "/api/reviewer/session", { body: { a: 1 } }))).status
    ).toBe(413);
    expect(backend).not.toHaveBeenCalled();
  });
});

describe("reviewer cookie parsing", () => {
  const names = cookieNamesFor("test");

  it("ignores duplicated, malformed, and unrelated cookies", () => {
    const header = (value: string) => new Headers({ Cookie: value });
    expect(
      readReviewerCookies(header(`sg_session=${sessionToken}; sg_csrf=${csrfToken}`), names)
    ).toEqual({
      session: sessionToken,
      csrf: csrfToken
    });
    expect(
      readReviewerCookies(
        header(`sg_session=${sessionToken}; sg_session=other-token-0123456789`),
        names
      )
    ).toEqual({});
    expect(readReviewerCookies(header("sg_session=short; other=1; noequals"), names)).toEqual({});
    expect(readReviewerCookies(new Headers(), names)).toEqual({});
    expect(cookieNamesFor("production").session).toBe("__Host-sg_session");
  });
});

type Ctx = Record<string, string>;
type ReadHandler = (request: Request, context: { params: Promise<Ctx> }) => Promise<Response>;
type MutationCase = {
  readonly name: string;
  readonly handler: (request: Request, context: { params: Promise<never> }) => Promise<Response>;
  readonly path: string;
  readonly ctx: Ctx;
  readonly body?: unknown;
  readonly backendPath: string;
  readonly success: () => Response;
  readonly successStatus: number;
};

const draft = {
  statement: "A fictional statement that is long enough.",
  effective_on: "2026-09-01",
  verification_state: "corroborated",
  citations: [
    { source_version_id: otherId, passage: "invented passage", location_label: "section 1" }
  ]
};
const base = `/api/reviewer/reports/${reportId}`;
const v1 = `/v1/reviewer/reports/${reportId}`;

const mutationCases: readonly MutationCase[] = [
  {
    name: "note",
    handler: createNote as never,
    path: `${base}/notes`,
    ctx: { reportId },
    body: { body: "private reviewer note text" },
    backendPath: `${v1}/notes`,
    success: () => okJson({ note_id: otherId }, 201),
    successStatus: 201
  },
  {
    name: "ask follow-up",
    handler: askFollowUp as never,
    path: `${base}/follow-up-questions`,
    ctx: { reportId },
    body: { question: "Where was the photo taken?" },
    backendPath: `${v1}/follow-up-questions`,
    success: () => okJson({ question_id: otherId }, 201),
    successStatus: 201
  },
  {
    name: "withdraw follow-up",
    handler: withdrawFollowUp as never,
    path: `${base}/follow-up-questions/${otherId}/withdraw`,
    ctx: { reportId, questionId: otherId },
    backendPath: `${v1}/follow-up-questions/${otherId}:withdraw`,
    success: () => new Response(null, { status: 204 }),
    successStatus: 204
  },
  {
    name: "status transition",
    handler: transition as never,
    path: `${base}/status-transition`,
    ctx: { reportId },
    body: { command: "start_review", expected_status: "received", expected_version: 1 },
    backendPath: `${v1}/status-transitions`,
    success: () => okJson({ status: "under_review", published: false }),
    successStatus: 200
  },
  {
    name: "publication draft",
    handler: createDraft as never,
    path: `${base}/public-updates`,
    ctx: { reportId },
    body: draft,
    backendPath: `${v1}/public-updates`,
    success: () => okJson({ can_publish: false }, 201),
    successStatus: 201
  },
  {
    name: "publish update",
    handler: publishUpdate as never,
    path: `${base}/public-updates/${otherId}/publish`,
    ctx: { reportId, updateId: otherId },
    body: { preview_digest: digest },
    backendPath: `${v1}/public-updates/${otherId}:publish`,
    success: () => okJson({ published: true }),
    successStatus: 200
  },
  {
    name: "withdraw update",
    handler: withdrawUpdate as never,
    path: `${base}/public-updates/${otherId}/withdraw`,
    ctx: { reportId, updateId: otherId },
    backendPath: `${v1}/public-updates/${otherId}:withdraw`,
    success: () => new Response(null, { status: 204 }),
    successStatus: 204
  },
  {
    name: "discovery plan",
    handler: planDiscovery as never,
    path: `${base}/discovery/plan`,
    ctx: { reportId },
    body: { concepts: ["school roof"] },
    backendPath: `${v1}/discovery-runs:plan`,
    success: () => okJson({ plan_digest: digest }),
    successStatus: 200
  },
  {
    name: "discovery create",
    handler: createRun as never,
    path: `${base}/discovery`,
    ctx: { reportId },
    body: { approved_digest: digest, concepts: [] },
    backendPath: `${v1}/discovery-runs`,
    success: () => okJson({ run_id: otherId }, 201),
    successStatus: 201
  },
  {
    name: "discovery cancel",
    handler: cancelRun as never,
    path: `/api/reviewer/discovery/${otherId}/cancel`,
    ctx: { runId: otherId },
    backendPath: `/v1/reviewer/discovery-runs/${otherId}:cancel`,
    success: () => okJson({ status: "cancelled" }),
    successStatus: 200
  },
  {
    name: "discovery review",
    handler: reviewRun as never,
    path: `/api/reviewer/discovery/${otherId}/review`,
    ctx: { runId: otherId },
    body: { command: "approve_completion" },
    backendPath: `/v1/reviewer/discovery-runs/${otherId}:review`,
    success: () => okJson({ status: "complete" }),
    successStatus: 200
  },
  {
    name: "discovery follow-up answer",
    handler: answerRun as never,
    path: `/api/reviewer/discovery/${otherId}/follow-up-answers`,
    ctx: { runId: otherId },
    body: { question_index: 0, kind: "answered", answer: "private answer" },
    backendPath: `/v1/reviewer/discovery-runs/${otherId}/follow-up-answers`,
    success: () => new Response(null, { status: 204 }),
    successStatus: 204
  },
  {
    name: "source decision",
    handler: decideSource as never,
    path: `/api/reviewer/discovered-sources/${otherId}/decision`,
    ctx: { sourceId: otherId },
    body: { command: "attach", reason: "matches the cited record" },
    backendPath: `/v1/reviewer/discovered-sources/${otherId}/decision`,
    success: () => okJson({ disposition: "attached_pending" }),
    successStatus: 200
  }
];

function call(spec: MutationCase, init: Parameters<typeof request>[2] = {}, ctx: Ctx = spec.ctx) {
  return spec.handler(request("POST", spec.path, { body: spec.body, ...init }), {
    params: Promise.resolve(ctx) as never
  });
}

describe.each(mutationCases)("reviewer $name handler", (spec) => {
  it("forwards session and CSRF from cookies to exactly one operation, never the cookie", async () => {
    backend.mockResolvedValueOnce(spec.success());

    const response = await call(spec, {
      headers: {
        "X-Shaidago-Locale": "yo",
        Authorization: "Bearer browser",
        "X-Forwarded-For": "203.0.113.9"
      }
    });

    const sent = sentAt(0);
    expect(sent.method).toBe("POST");
    expect(new URL(sent.url).pathname).toBe(spec.backendPath);
    expect(sent.headers.get("Authorization")).toBe(`Bearer web.${credential}`);
    expect(sent.headers.get("X-Shaidago-Session")).toBe(sessionToken);
    expect(sent.headers.get("X-Shaidago-Csrf")).toBe(csrfToken);
    expect(sent.headers.get("X-Shaidago-Locale")).toBe("yo");
    expect(sent.headers.get("Cookie")).toBeNull();
    expect(sent.headers.get("X-Forwarded-For")).toBeNull();
    expect(response.status).toBe(spec.successStatus);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.getSetCookie()).toEqual([]);
    expect(sent.url).not.toContain(sessionToken);
  });

  it("checks Origin first, then the session (401 clears cookies), then CSRF", async () => {
    const foreign = await call(spec, { headers: { Origin: "https://evil.example" }, cookie: null });
    expect(foreign.status).toBe(403);
    expect(((await foreign.json()) as { code: string }).code).toBe("origin_forbidden");

    const anonymous = await call(spec, { cookie: null });
    expect(anonymous.status).toBe(401);
    expect(anonymous.headers.getSetCookie()).toHaveLength(2);

    const noCsrf = await call(spec, { cookie: `sg_session=${sessionToken}` });
    expect(noCsrf.status).toBe(403);
    expect(((await noCsrf.json()) as { code: string }).code).toBe("csrf_invalid");
    expect(backend).not.toHaveBeenCalled();
  });

  it("treats a malformed identifier as not found without contacting the API", async () => {
    const ctx = Object.fromEntries(Object.keys(spec.ctx).map((key) => [key, "not-a-uuid"]));
    const response = await call(spec, {}, ctx);
    expect(response.status).toBe(404);
    expect(((await response.json()) as { code: string }).code).toBe("not_found");
    expect(backend).not.toHaveBeenCalled();
  });

  it("clears cookies when the API rejects the session and stays non-disclosing on 403 and 409", async () => {
    backend.mockResolvedValueOnce(problemJson("unauthenticated", 401));
    const expired = await call(spec);
    expect(expired.status).toBe(401);
    expect(expired.headers.getSetCookie()).toHaveLength(2);

    backend.mockResolvedValueOnce(problemJson("forbidden", 403));
    const forbidden = await call(spec);
    expect(forbidden.status).toBe(403);
    expect(forbidden.headers.getSetCookie()).toEqual([]);
    expect(await forbidden.text()).not.toContain("secret backend detail");

    backend.mockResolvedValueOnce(problemJson("report_version_conflict", 409));
    const conflict = await call(spec);
    expect(conflict.status).toBe(409);
    expect(((await conflict.json()) as { code: string }).code).toBe("report_version_conflict");
  });

  it("maps a timeout to 504 and never retries a mutation", async () => {
    backend.mockRejectedValueOnce(new DOMException("timed out", "TimeoutError"));
    expect((await call(spec)).status).toBe(504);
    backend.mockRejectedValueOnce(new TypeError("fetch failed"));
    expect((await call(spec)).status).toBe(503);
    expect(backend).toHaveBeenCalledTimes(2);
  });

  it("stops and reports cancellation when the browser disconnects", async () => {
    const controller = new AbortController();
    backend.mockImplementationOnce(async (input) => {
      controller.abort();
      throw (input as Request).signal.reason ?? new DOMException("aborted", "AbortError");
    });

    const response = await spec.handler(
      new Request(`${origin}${spec.path}`, {
        method: "POST",
        headers: {
          Origin: origin,
          Cookie: cookies,
          ...(spec.body === undefined ? {} : { "Content-Type": "application/json" })
        },
        body: spec.body === undefined ? null : JSON.stringify(spec.body),
        signal: controller.signal
      }),
      { params: Promise.resolve(spec.ctx) as never }
    );

    expect(response.status).toBe(499);
    expect(backend).toHaveBeenCalledTimes(1);
  });

  it("rejects the wrong body shape or content type before the API", async () => {
    if (spec.body === undefined) {
      const withBody = await call(spec, { body: { unexpected: true } });
      expect(withBody.status).toBe(413);
    } else {
      expect((await call(spec, { headers: { "Content-Type": "text/plain" } })).status).toBe(415);
      const unknown = await call(spec, {
        body: { ...(spec.body as object), surprise: "leaked-123" }
      });
      expect(unknown.status).toBe(422);
      expect(await unknown.text()).not.toContain("leaked-123");
      expect((await call(spec, { body: { pad: "x".repeat(20_000) } })).status).toBe(413);
    }
    expect(backend).not.toHaveBeenCalled();
  });
});

describe("reviewer transition and enumerations", () => {
  it("passes an allowed command through without deciding whether it is valid", async () => {
    backend.mockResolvedValueOnce(problemJson("report_status_transition_not_allowed", 409));
    const response = await call(mutationCases[3]!, {
      body: { command: "record_follow_up", expected_status: "received", expected_version: 1 }
    });
    expect(response.status).toBe(409);
    expect(JSON.parse(await sentAt(0).text())).toMatchObject({ command: "record_follow_up" });
  });

  it("rejects unknown commands, statuses, and non-positive versions locally", async () => {
    for (const body of [
      { command: "publish", expected_status: "received", expected_version: 1 },
      { command: "close", expected_status: "published", expected_version: 1 },
      { command: "close", expected_status: "received", expected_version: 0 }
    ]) {
      expect((await call(mutationCases[3]!, { body })).status).toBe(422);
    }
    expect(backend).not.toHaveBeenCalled();
  });

  it("keeps optional reasons out of the forwarded body when omitted", async () => {
    backend.mockResolvedValueOnce(okJson({ status: "closed" }));
    await call(mutationCases[3]!, {
      body: {
        command: "close",
        expected_status: "received",
        expected_version: 2,
        internal_reason: null
      }
    });
    expect(JSON.parse(await sentAt(0).text())).toEqual({
      command: "close",
      expected_status: "received",
      expected_version: 2,
      internal_reason: null
    });
  });
});

describe("reviewer read handlers", () => {
  const readCases = [
    {
      name: "publication preview",
      handler: previewUpdate as unknown as ReadHandler,
      path: `${base}/public-updates/${otherId}`,
      ctx: { reportId, updateId: otherId },
      backendPath: `${v1}/public-updates/${otherId}`
    },
    {
      name: "discovery run",
      handler: getRun as unknown as ReadHandler,
      path: `/api/reviewer/discovery/${otherId}`,
      ctx: { runId: otherId },
      backendPath: `/v1/reviewer/discovery-runs/${otherId}`
    }
  ] as const;

  it.each(readCases)("$name requires a session, forwards it, and is never cached", async (spec) => {
    const anonymous = await spec.handler(request("GET", spec.path, { cookie: null }), {
      params: Promise.resolve(spec.ctx)
    });
    expect(anonymous.status).toBe(401);
    expect(anonymous.headers.getSetCookie()).toHaveLength(2);
    expect(backend).not.toHaveBeenCalled();

    backend.mockResolvedValueOnce(okJson({ status: "needs_review" }));
    const response = await spec.handler(request("GET", spec.path), {
      params: Promise.resolve(spec.ctx)
    });
    const sent = sentAt(0);
    expect(sent.method).toBe("GET");
    expect(new URL(sent.url).pathname).toBe(spec.backendPath);
    expect(sent.headers.get("X-Shaidago-Session")).toBe(sessionToken);
    expect(sent.headers.get("X-Shaidago-Csrf")).toBeNull();
    expect(sent.headers.get("Cookie")).toBeNull();
    expect(response.headers.get("Cache-Control")).toBe("no-store");
  });

  it.each(readCases)("$name retries once on a transient 503 and rejects bad IDs", async (spec) => {
    backend
      .mockResolvedValueOnce(problemJson("dependency_unavailable", 503))
      .mockResolvedValueOnce(okJson({ status: "needs_review" }));
    const response = await spec.handler(request("GET", spec.path), {
      params: Promise.resolve(spec.ctx)
    });
    expect(response.status).toBe(200);
    expect(backend).toHaveBeenCalledTimes(2);

    const bad = await spec.handler(request("GET", spec.path), {
      params: Promise.resolve({ reportId: "x", updateId: "y", runId: "z" })
    });
    expect(bad.status).toBe(404);
  });
});

describe("evidence download broker", () => {
  const path = `${base}/evidence/${otherId}`;
  const params = { params: Promise.resolve({ reportId, evidenceId: otherId }) };

  it("streams the file with re-asserted security headers and no backend passthrough", async () => {
    backend.mockResolvedValueOnce(
      new Response(new Uint8Array([1, 2, 3]), {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": 'attachment; filename="evidence.pdf"',
          "X-Evidence-Scan-State": "not_scanned_demo",
          "X-Storage-Key": "reports/secret-object-key",
          "Set-Cookie": "leak=1"
        }
      })
    );

    const response = await downloadEvidence(request("GET", path), params);

    expect(response.status).toBe(200);
    expect(new Uint8Array(await response.arrayBuffer())).toEqual(new Uint8Array([1, 2, 3]));
    expect(response.headers.get("Content-Type")).toBe("application/pdf");
    expect(response.headers.get("Content-Disposition")).toBe('attachment; filename="evidence.pdf"');
    expect(response.headers.get("X-Content-Type-Options")).toBe("nosniff");
    expect(response.headers.get("Content-Security-Policy")).toBe("default-src 'none'; sandbox");
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.get("X-Evidence-Scan-State")).toBe("not_scanned_demo");
    expect(response.headers.get("X-Storage-Key")).toBeNull();
    expect(response.headers.getSetCookie()).toEqual([]);
    expect(new URL(sentAt(0).url).pathname).toBe(`${v1}/evidence/${otherId}/content`);
    expect(sentAt(0).headers.get("X-Shaidago-Session")).toBe(sessionToken);
  });

  it("downgrades an unexpected type or disposition rather than forwarding it", async () => {
    backend.mockResolvedValueOnce(
      new Response("<script>alert(1)</script>", {
        status: 200,
        headers: {
          "Content-Type": "text/html",
          "Content-Disposition": 'inline; filename="x.html"',
          "X-Evidence-Scan-State": "surprising"
        }
      })
    );
    const response = await downloadEvidence(request("GET", path), params);
    expect(response.headers.get("Content-Type")).toBe("application/octet-stream");
    expect(response.headers.get("Content-Disposition")).toBe("attachment");
    expect(response.headers.get("X-Evidence-Scan-State")).toBeNull();
  });

  it("requires a session, treats a bad ID as not found, and maps failures to safe problems", async () => {
    expect((await downloadEvidence(request("GET", path, { cookie: null }), params)).status).toBe(
      401
    );
    expect(
      (
        await downloadEvidence(request("GET", path), {
          params: Promise.resolve({ reportId, evidenceId: "nope" })
        })
      ).status
    ).toBe(404);
    expect(backend).not.toHaveBeenCalled();

    backend.mockResolvedValueOnce(problemJson("not_found", 404));
    const missing = await downloadEvidence(request("GET", path), params);
    expect(missing.status).toBe(404);
    expect(await missing.text()).not.toContain("secret backend detail");

    backend.mockResolvedValueOnce(problemJson("dependency_unavailable", 503));
    expect((await downloadEvidence(request("GET", path), params)).status).toBe(503);
    expect(backend).toHaveBeenCalledTimes(2);
  });
});

describe("reviewer route surface", () => {
  function routeFiles(directory: string): string[] {
    return readdirSync(directory).flatMap((name) => {
      const path = join(directory, name);

      if (statSync(path).isDirectory()) {
        return routeFiles(path);
      }

      return name === "route.ts" ? [path] : [];
    });
  }

  it("exposes only the declared methods and never caches", () => {
    const root = join(import.meta.dirname, "..", "..", "app", "api", "reviewer");
    const files = routeFiles(root);

    expect(files).toHaveLength(17);

    for (const file of files) {
      const source = readFileSync(file, "utf8");
      const methods = [
        ...source.matchAll(
          /^export (?:async )?function (GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b/gm
        )
      ];

      expect(methods, file).toHaveLength(file.endsWith("session/route.ts") ? 2 : 1);
      expect(source, file).toContain('export const dynamic = "force-dynamic";');
      expect(source, file).toContain('export const runtime = "nodejs";');
    }
  });
});
