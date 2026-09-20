import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { POST as askQuestion } from "../../app/api/public/questions/route";
import { POST as startDiscovery } from "../../app/api/public/discovery/route";
import { GET as pollDiscovery } from "../../app/api/public/discovery/[runId]/route";
import { POST as submitReport } from "../../app/api/reports/route";
import { POST as lookupStatus } from "../../app/api/tracking/lookup/route";
import { POST as answerFollowUp } from "../../app/api/tracking/follow-up/route";
import { POST as createHandle } from "../../app/api/reporter-handle/route";
import { POST as listHandleReports } from "../../app/api/reporter-handle/reports/route";
import { POST as deleteHandle } from "../../app/api/reporter-handle/delete/route";

const origin = "http://localhost:3000";
const credential = "shaida-go-unit-test-credential-not-a-secret";
const key = "0198f1a2-7b3c-4d4e-8f5a-123456789abc";
const runId = "0198f1a2-7b3c-4d4e-8f5a-123456789abd";
const secretCode = "SG-TRACK-SECRET-CODE";
const problemJson = (code: string, status: number, headers: Record<string, string> = {}) =>
  new Response(
    JSON.stringify({
      type: "about:blank",
      title: "Backend title",
      status,
      code,
      detail: "backend detail with 10.0.0.9 and stack"
    }),
    { status, headers: { "Content-Type": "application/problem+json", ...headers } }
  );
const okJson = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers }
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

function json(path: string, body: unknown, headers: Record<string, string> = {}): Request {
  return new Request(`${origin}${path}`, {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body)
  });
}

function sent(): Request {
  const request = backend.mock.calls[0]?.[0];

  if (!(request instanceof Request)) {
    throw new Error("expected a backend request");
  }

  return request;
}

type JsonCase = {
  readonly name: string;
  readonly handler: (request: Request) => Promise<Response>;
  readonly path: string;
  readonly body: unknown;
  readonly headers?: Record<string, string>;
  readonly backendPath: string;
  readonly backendBody: unknown;
  readonly success: Response;
  readonly successStatus: number;
  readonly sensitive: readonly string[];
};

const jsonCases: readonly JsonCase[] = [
  {
    name: "project question",
    handler: askQuestion,
    path: "/api/public/questions",
    body: { slug: "synthetic-example-clinic", question: "When was this last checked?" },
    backendPath: "/v1/projects/synthetic-example-clinic/questions",
    backendBody: { question: "When was this last checked?" },
    success: okJson({ answer: "x" }),
    successStatus: 200,
    sensitive: []
  },
  {
    name: "public discovery start",
    handler: startDiscovery,
    path: "/api/public/discovery",
    body: { slug: "synthetic-example-clinic" },
    backendPath: "/v1/projects/synthetic-example-clinic/discovery-runs",
    backendBody: undefined,
    success: okJson({ action: "create", run_id: runId }),
    successStatus: 200,
    sensitive: []
  },
  {
    name: "tracking lookup",
    handler: lookupStatus,
    path: "/api/tracking/lookup",
    body: { code: secretCode },
    backendPath: "/v1/report-status:lookup",
    backendBody: { code: secretCode },
    success: okJson({ status: "received" }),
    successStatus: 200,
    sensitive: [secretCode]
  },
  {
    name: "follow-up answer",
    handler: answerFollowUp,
    path: "/api/tracking/follow-up",
    body: { question_id: runId, kind: "answered", answer: "private answer text", code: secretCode },
    headers: { "Idempotency-Key": key },
    backendPath: "/v1/report-status:answer-follow-up",
    backendBody: {
      question_id: runId,
      kind: "answered",
      answer: "private answer text",
      code: secretCode
    },
    success: okJson({ accepted: true }),
    successStatus: 200,
    sensitive: [secretCode, "private answer text"]
  },
  {
    name: "handle report list",
    handler: listHandleReports,
    path: "/api/reporter-handle/reports",
    body: { handle: "SG-H-AAAA-BBBB", passphrase: "six secret words go right here now" },
    backendPath: "/v1/reporter-handles:list-reports",
    backendBody: { handle: "SG-H-AAAA-BBBB", passphrase: "six secret words go right here now" },
    success: okJson({ reports: [] }),
    successStatus: 200,
    sensitive: ["six secret words"]
  },
  {
    name: "handle delete",
    handler: deleteHandle,
    path: "/api/reporter-handle/delete",
    body: { handle: "SG-H-AAAA-BBBB", passphrase: "six secret words go right here now" },
    backendPath: "/v1/reporter-handles:delete",
    backendBody: { handle: "SG-H-AAAA-BBBB", passphrase: "six secret words go right here now" },
    success: new Response(null, { status: 204 }),
    successStatus: 204,
    sensitive: ["six secret words"]
  }
];

describe.each(jsonCases)("$name handler", (spec) => {
  it("calls exactly its backend operation with the internal credential and no browser secrets", async () => {
    backend.mockResolvedValueOnce(spec.success.clone());

    const response = await spec.handler(
      json(spec.path, spec.body, {
        ...spec.headers,
        Cookie: "sg_session=browser-session",
        Authorization: "Bearer browser-supplied",
        "X-Forwarded-For": "203.0.113.9",
        "X-Shaidago-Locale": "ig"
      })
    );

    const request = sent();
    expect(request.method).toBe("POST");
    expect(new URL(request.url).pathname + new URL(request.url).search).toBe(spec.backendPath);
    expect(request.headers.get("Authorization")).toBe(`Bearer web.${credential}`);
    expect(request.headers.get("Cookie")).toBeNull();
    expect(request.headers.get("X-Forwarded-For")).toBeNull();
    expect(request.headers.get("X-Shaidago-Locale")).toBe("ig");
    for (const secret of spec.sensitive) {
      expect(request.url).not.toContain(secret);
    }
    if (spec.backendBody !== undefined) {
      expect(JSON.parse(await request.text())).toEqual(spec.backendBody);
    }
    expect(response.status).toBe(spec.successStatus);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.get("X-Request-Id")).toMatch(/^[0-9a-f-]{36}$/);
    expect(response.headers.get("Set-Cookie")).toBeNull();
  });

  it("refuses a missing, foreign, or repeated Origin before calling the backend", async () => {
    for (const badOrigin of [
      undefined,
      "https://evil.example",
      `${origin}, https://evil.example`
    ]) {
      const request = json(spec.path, spec.body, spec.headers);
      request.headers.delete("Origin");
      if (badOrigin !== undefined) {
        request.headers.set("Origin", badOrigin);
      }
      const response = await spec.handler(request);
      expect(response.status).toBe(403);
      expect(((await response.json()) as { code: string }).code).toBe("origin_forbidden");
      expect(response.headers.get("Cache-Control")).toBe("no-store");
    }
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejects a wrong content type and an oversized body before calling the backend", async () => {
    const wrongType = json(spec.path, spec.body, { ...spec.headers, "Content-Type": "text/plain" });
    expect((await spec.handler(wrongType)).status).toBe(415);

    const oversized = json(spec.path, { padding: "x".repeat(20_000) }, spec.headers);
    expect((await spec.handler(oversized)).status).toBe(413);
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejects malformed JSON and unknown fields without echoing values", async () => {
    const malformed = new Request(`${origin}${spec.path}`, {
      method: "POST",
      headers: { Origin: origin, "Content-Type": "application/json", ...spec.headers },
      body: "{not json"
    });
    expect((await spec.handler(malformed)).status).toBe(400);

    const unknown = await spec.handler(
      json(spec.path, { ...(spec.body as object), surprise: "leaked-value-123" }, spec.headers)
    );
    expect(unknown.status).toBe(422);
    expect(await unknown.text()).not.toContain("leaked-value-123");
    expect(backend).not.toHaveBeenCalled();
  });

  it("maps a backend problem to a safe stable code with no backend detail", async () => {
    backend.mockResolvedValueOnce(problemJson("rate_limited", 429, { "Retry-After": "12" }));

    const response = await spec.handler(json(spec.path, spec.body, spec.headers));
    const text = await response.text();

    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("12");
    expect(response.headers.get("Content-Type")).toBe("application/problem+json");
    expect(JSON.parse(text)).toMatchObject({ code: "rate_limited" });
    expect(text).not.toMatch(/10\.0\.0\.9|stack|Backend title|api\.internal/);
  });

  it("maps a backend timeout to 504 and does not retry the mutation", async () => {
    backend.mockRejectedValueOnce(new DOMException("timed out", "TimeoutError"));

    const response = await spec.handler(json(spec.path, spec.body, spec.headers));

    expect(response.status).toBe(504);
    expect(((await response.json()) as { code: string }).code).toBe("upstream_timeout");
    expect(backend).toHaveBeenCalledTimes(1);
  });

  it("does not retry after a network failure", async () => {
    backend.mockRejectedValue(new TypeError("fetch failed: 10.0.0.9"));

    const response = await spec.handler(json(spec.path, spec.body, spec.headers));

    expect(response.status).toBe(503);
    expect(await response.text()).not.toContain("10.0.0.9");
    expect(backend).toHaveBeenCalledTimes(1);
  });

  it("stops and reports cancellation when the browser disconnects", async () => {
    const controller = new AbortController();
    backend.mockImplementationOnce(async (input) => {
      controller.abort();
      const signal = (input as Request).signal;
      throw signal.reason ?? new DOMException("aborted", "AbortError");
    });
    const request = new Request(`${origin}${spec.path}`, {
      method: "POST",
      headers: { Origin: origin, "Content-Type": "application/json", ...spec.headers },
      body: JSON.stringify(spec.body),
      signal: controller.signal
    });

    const response = await spec.handler(request);

    expect(response.status).toBe(499);
    expect(backend).toHaveBeenCalledTimes(1);
  });
});

describe("idempotent handlers", () => {
  it("require a valid key and forward it unchanged", async () => {
    const body = { question_id: runId, kind: "skipped", code: secretCode };
    expect((await answerFollowUp(json("/api/tracking/follow-up", body))).status).toBe(400);
    expect(
      (await answerFollowUp(json("/api/tracking/follow-up", body, { "Idempotency-Key": "abc" })))
        .status
    ).toBe(400);
    expect(backend).not.toHaveBeenCalled();

    backend.mockResolvedValueOnce(
      okJson({ accepted: true }, 200, { "Idempotency-Replayed": "true" })
    );
    const response = await answerFollowUp(
      json("/api/tracking/follow-up", body, { "Idempotency-Key": key })
    );
    expect(sent().headers.get("Idempotency-Key")).toBe(key);
    expect(response.headers.get("Idempotency-Replayed")).toBe("true");
  });

  it("surfaces a conflicting reuse as a stable code", async () => {
    backend.mockResolvedValueOnce(problemJson("idempotency_conflict", 409));
    const response = await answerFollowUp(
      json(
        "/api/tracking/follow-up",
        { question_id: runId, kind: "skipped", code: secretCode },
        {
          "Idempotency-Key": key
        }
      )
    );
    expect(response.status).toBe(409);
    expect(((await response.json()) as { code: string }).code).toBe("idempotency_conflict");
  });

  it("requires exactly one credential form for follow-up answers", async () => {
    for (const credentials of [
      {},
      { code: secretCode, handle: "SG-H-AAAA-BBBB", passphrase: "p" },
      { handle: "SG-H-AAAA-BBBB" }
    ]) {
      const response = await answerFollowUp(
        json(
          "/api/tracking/follow-up",
          { question_id: runId, kind: "skipped", ...credentials },
          {
            "Idempotency-Key": key
          }
        )
      );
      expect(response.status).toBe(422);
    }
    expect(backend).not.toHaveBeenCalled();
  });

  it("creates a handle with an empty body, a key, and no-store, and rejects a body", async () => {
    const empty = (headers: Record<string, string>, body?: string) =>
      new Request(`${origin}/api/reporter-handle`, {
        method: "POST",
        headers: { Origin: origin, ...headers },
        body: body ?? null
      });

    expect((await createHandle(empty({}))).status).toBe(400);
    expect((await createHandle(empty({ "Idempotency-Key": key }, "{}"))).status).toBe(413);
    expect(backend).not.toHaveBeenCalled();

    backend.mockResolvedValueOnce(okJson({ handle: "SG-H-AAAA-BBBB", recoverable: false }, 201));
    const response = await createHandle(empty({ "Idempotency-Key": key }));
    expect(response.status).toBe(201);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(new URL(sent().url).pathname).toBe("/v1/reporter-handles");
  });
});

describe("report submission handler", () => {
  function multipart(headers: Record<string, string> = { "Idempotency-Key": key }): Request {
    const form = new FormData();
    form.set("project_slug", "synthetic-example");
    form.set("description", "A fictional report body long enough to pass.");
    form.set(
      "attachments",
      new File([new Uint8Array([1, 2, 3])], "photo.jpg", { type: "image/jpeg" })
    );

    return new Request(`${origin}/api/reports`, {
      method: "POST",
      headers: { Origin: origin, ...headers },
      body: form
    });
  }

  it("streams the multipart body to its one operation, preserving the boundary", async () => {
    backend.mockImplementationOnce(async (input) => {
      const text = await (input as Request).text();
      expect(text).toContain("A fictional report body");
      return okJson({ tracking_code: "one-time", status: "received" }, 201);
    });

    const response = await submitReport(multipart());
    const request = sent();

    expect(response.status).toBe(201);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(new URL(request.url).pathname).toBe("/v1/reports");
    expect(request.headers.get("Content-Type")).toMatch(/^multipart\/form-data; boundary=/);
    expect(request.headers.get("Idempotency-Key")).toBe(key);
    expect(request.url).not.toContain("fictional");
  });

  it("requires Origin, a key, and multipart content", async () => {
    const noOrigin = multipart();
    noOrigin.headers.delete("Origin");
    expect((await submitReport(noOrigin)).status).toBe(403);
    expect((await submitReport(multipart({}))).status).toBe(400);
    const json = new Request(`${origin}/api/reports`, {
      method: "POST",
      headers: { Origin: origin, "Content-Type": "application/json", "Idempotency-Key": key },
      body: "{}"
    });
    expect((await submitReport(json)).status).toBe(415);
    expect(backend).not.toHaveBeenCalled();
  });

  it("rejects an oversized declared length without contacting the backend", async () => {
    const request = multipart();
    request.headers.set("Content-Length", String(31 * 1024 * 1024 + 1));
    expect((await submitReport(request)).status).toBe(413);
    expect(backend).not.toHaveBeenCalled();
  });

  it("stops a streamed body that exceeds the cap even without a declared length", async () => {
    const chunk = new Uint8Array(1024 * 1024);
    let sentChunks = 0;
    const stream = new ReadableStream<Uint8Array>({
      pull(controller) {
        sentChunks += 1;
        if (sentChunks > 40) {
          controller.close();
          return;
        }
        controller.enqueue(chunk);
      }
    });
    backend.mockImplementationOnce(async (input) => {
      await (input as Request).arrayBuffer();
      return okJson({}, 201);
    });
    const request = new Request(`${origin}/api/reports`, {
      method: "POST",
      headers: {
        Origin: origin,
        "Content-Type": "multipart/form-data; boundary=abc",
        "Idempotency-Key": key
      },
      body: stream,
      duplex: "half"
    } as RequestInit);

    const response = await submitReport(request);

    expect(response.status).toBe(413);
    expect(sentChunks).toBeLessThan(40);
  });

  it("preserves a partial-attachment receipt and maps backend problems and timeouts", async () => {
    backend.mockResolvedValueOnce(
      okJson(
        {
          status: "received",
          attachments: [{ position: 1, kept: false, reason: "unsupported_type" }]
        },
        201
      )
    );
    const partial = await submitReport(multipart());
    expect(await partial.json()).toMatchObject({ attachments: [{ kept: false }] });

    backend.mockResolvedValueOnce(problemJson("payload_too_large", 413));
    expect((await submitReport(multipart())).status).toBe(413);

    backend.mockRejectedValueOnce(new DOMException("timed out", "TimeoutError"));
    expect((await submitReport(multipart())).status).toBe(504);
  });
});

describe("public discovery poll handler", () => {
  function get(path: string): NextRequest {
    return new NextRequest(`${origin}${path}`, { headers: { Cookie: "sg_session=x" } });
  }
  const context = (id: string) => ({ params: Promise.resolve({ runId: id }) });

  it("polls one run with an optional version and never forwards cookies", async () => {
    backend.mockResolvedValueOnce(okJson({ status: "searching", version: 3 }));

    const response = await pollDiscovery(
      get(`/api/public/discovery/${runId}?since_version=2`),
      context(runId)
    );
    const request = sent();

    expect(request.method).toBe("GET");
    expect(new URL(request.url).pathname + new URL(request.url).search).toBe(
      `/v1/discovery-runs/${runId}?since_version=2`
    );
    expect(request.headers.get("Cookie")).toBeNull();
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
  });

  it("answers a 304 without a body and rejects extra or invalid parameters", async () => {
    backend.mockResolvedValueOnce(new Response(null, { status: 304 }));
    const unchanged = await pollDiscovery(
      get(`/api/public/discovery/${runId}?since_version=3`),
      context(runId)
    );
    expect(unchanged.status).toBe(304);
    expect(unchanged.headers.get("Cache-Control")).toBe("no-store");

    for (const path of [
      `/api/public/discovery/${runId}?extra=1`,
      `/api/public/discovery/${runId}?since_version=-1`,
      `/api/public/discovery/${runId}?since_version=1&since_version=2`,
      `/api/public/discovery/${runId}?since_version=abc`
    ]) {
      expect((await pollDiscovery(get(path), context(runId))).status, path).toBe(422);
    }
    expect(
      (await pollDiscovery(get("/api/public/discovery/not-a-uuid"), context("not-a-uuid"))).status
    ).toBe(422);
    expect(backend).toHaveBeenCalledTimes(1);
  });

  it("reports cancellation when the browser disconnects mid-poll", async () => {
    const controller = new AbortController();
    backend.mockImplementationOnce(async (input) => {
      controller.abort();
      throw (input as Request).signal.reason ?? new DOMException("aborted", "AbortError");
    });

    const response = await pollDiscovery(
      new NextRequest(`${origin}/api/public/discovery/${runId}`, { signal: controller.signal }),
      context(runId)
    );

    expect(response.status).toBe(499);
  });

  it("maps a missing run and a timeout to safe problems", async () => {
    backend.mockResolvedValueOnce(problemJson("not_found", 404));
    expect(
      (await pollDiscovery(get(`/api/public/discovery/${runId}`), context(runId))).status
    ).toBe(404);

    backend.mockRejectedValueOnce(new DOMException("timed out", "TimeoutError"));
    expect(
      (await pollDiscovery(get(`/api/public/discovery/${runId}`), context(runId))).status
    ).toBe(504);
  });
});

describe("client HMAC forwarding", () => {
  it("forwards a pseudonym from the trusted address and never the address or a spoofed left entry", async () => {
    vi.stubEnv("CLIENT_HMAC_KEY", Buffer.alloc(32, 5).toString("base64"));
    backend.mockResolvedValueOnce(okJson({ status: "received" }));

    await lookupStatus(
      json(
        "/api/tracking/lookup",
        { code: secretCode },
        { "X-Forwarded-For": "6.6.6.6, 203.0.113.9" }
      )
    );

    const request = sent();
    expect(request.headers.get("X-Shaidago-Client-Hmac")).toMatch(/^[0-9a-f]{64}$/);
    expect(request.headers.get("X-Forwarded-For")).toBeNull();
    expect([...request.headers].join(" ")).not.toMatch(/203\.0\.113\.9|6\.6\.6\.6/);
  });

  it("sends no HMAC when no key is configured", async () => {
    backend.mockResolvedValueOnce(okJson({ status: "received" }));
    await lookupStatus(
      json("/api/tracking/lookup", { code: secretCode }, { "X-Forwarded-For": "203.0.113.9" })
    );
    expect(sent().headers.get("X-Shaidago-Client-Hmac")).toBeNull();
  });
});

describe("handler failure containment", () => {
  it("returns a generic 500 with no detail when configuration is invalid", async () => {
    vi.stubEnv("API_INTERNAL_URL", "");

    const response = await lookupStatus(json("/api/tracking/lookup", { code: secretCode }));
    const text = await response.text();

    expect(response.status).toBe(500);
    expect(JSON.parse(text)).toMatchObject({ code: "internal_error" });
    expect(text).not.toContain(secretCode);
    expect(text).not.toMatch(/API_INTERNAL_URL|environment/i);
  });

  it("exposes no method other than its declared one", async () => {
    const modules = await Promise.all(
      [
        "../../app/api/public/questions/route",
        "../../app/api/public/discovery/route",
        "../../app/api/public/discovery/[runId]/route",
        "../../app/api/reports/route",
        "../../app/api/tracking/lookup/route",
        "../../app/api/tracking/follow-up/route",
        "../../app/api/reporter-handle/route",
        "../../app/api/reporter-handle/reports/route",
        "../../app/api/reporter-handle/delete/route"
      ].map((path) => import(path) as Promise<Record<string, unknown>>)
    );

    for (const routeModule of modules) {
      const methods = Object.keys(routeModule).filter((name) =>
        ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"].includes(name)
      );
      expect(methods).toHaveLength(1);
      expect(routeModule["dynamic"]).toBe("force-dynamic");
    }
  });
});
