import { describe, expect, it } from "vitest";

import { BodyRejectedError, limitBodyStream, readBoundedJson } from "@/lib/bff/body";
import {
  BACKEND_HEADER_ALLOWLIST,
  BackendRequestError,
  backendSignal,
  buildBackendHeaders,
  classifyAbort
} from "@/lib/bff/backend-request";
import { verifyCsrfToken } from "@/lib/bff/csrf";
import { guardMutation } from "@/lib/bff/guard";
import { newIdempotencyKey, toIdempotencyKey } from "@/lib/bff/idempotency";
import { checkOrigin, resolveOriginPolicy } from "@/lib/bff/origin";
import {
  abortedResponse,
  apiProblemResponse,
  bodyRejectedResponse,
  problemResponse,
  unavailableResponse
} from "@/lib/bff/problem";

const requestId = "0198f1a2-7b3c-7d4e-8f5a-123456789abc";
const origin = "https://shaidago.example";
const policy = resolveOriginPolicy({
  appEnvironment: "production",
  publicOrigin: origin,
  requestUrl: "http://10.0.0.5:3000/api/x"
});
const token = "A".repeat(43);

function post(headers: Record<string, string>, body?: BodyInit): Request {
  return new Request("http://10.0.0.5:3000/api/x", { method: "POST", headers, body: body ?? null });
}

describe("origin policy", () => {
  it("trusts only the configured origin in deployed stages, ignoring forwarded headers", () => {
    expect(policy.allowedOrigins).toEqual([origin]);
    const spoofed = new Headers({
      Origin: "https://evil.example",
      "X-Forwarded-Host": "shaidago.example",
      "X-Forwarded-Proto": "https",
      Forwarded: "host=shaidago.example;proto=https"
    });
    expect(checkOrigin(spoofed, policy).ok).toBe(false);
    expect(checkOrigin(new Headers({ Origin: origin }), policy).ok).toBe(true);
  });

  it("refuses everything in a deployed stage with no configured origin", () => {
    const unconfigured = resolveOriginPolicy({
      appEnvironment: "staging",
      publicOrigin: undefined,
      requestUrl: "https://shaidago.example/api/x"
    });
    expect(unconfigured.allowedOrigins).toEqual([]);
    expect(checkOrigin(new Headers({ Origin: origin }), unconfigured).ok).toBe(false);
  });

  it("trusts the local request origin in development and test only", () => {
    const local = resolveOriginPolicy({
      appEnvironment: "development",
      publicOrigin: undefined,
      requestUrl: "http://localhost:3000/api/x"
    });
    expect(checkOrigin(new Headers({ Origin: "http://localhost:3000" }), local).ok).toBe(true);
    expect(checkOrigin(new Headers({ Origin: "http://localhost:3001" }), local).ok).toBe(false);
  });

  it("rejects missing, null, repeated, path-bearing, and cross-site origins", () => {
    for (const value of [
      undefined,
      "null",
      `${origin}, https://evil.example`,
      `${origin}/`,
      `${origin}/path`,
      "not a url",
      "javascript:alert(1)",
      "https://shaidago.example:8443"
    ]) {
      const headers = new Headers(value === undefined ? {} : { Origin: value });
      expect(checkOrigin(headers, policy).ok, String(value)).toBe(false);
    }
    expect(
      checkOrigin(new Headers({ Origin: origin, "Sec-Fetch-Site": "cross-site" }), policy).ok
    ).toBe(false);
    expect(
      checkOrigin(new Headers({ Origin: origin, "Sec-Fetch-Site": "same-origin" }), policy).ok
    ).toBe(true);
  });

  it("ignores an unparseable or non-http configured origin", () => {
    expect(
      resolveOriginPolicy({
        appEnvironment: "production",
        publicOrigin: "ftp://x",
        requestUrl: "http://a"
      }).allowedOrigins
    ).toEqual([]);
    expect(
      resolveOriginPolicy({
        appEnvironment: "production",
        publicOrigin: "nope",
        requestUrl: "http://a"
      }).allowedOrigins
    ).toEqual([]);
  });
});

describe("CSRF verification", () => {
  it("accepts only equal, well-formed tokens", () => {
    expect(verifyCsrfToken(token, token).ok).toBe(true);
    expect(verifyCsrfToken(token, "B".repeat(43)).ok).toBe(false);
    expect(verifyCsrfToken(undefined, token).ok).toBe(false);
    expect(verifyCsrfToken(token, undefined).ok).toBe(false);
    expect(verifyCsrfToken("short", "short").ok).toBe(false);
    expect(verifyCsrfToken(`${token}!`, `${token}!`).ok).toBe(false);
    expect(verifyCsrfToken(token, `${token}A`).ok).toBe(false);
  });
});

describe("idempotency keys", () => {
  it("accepts only lower-case canonical UUIDs and generates valid keys", () => {
    expect(toIdempotencyKey(requestId)).toBe(requestId);
    expect(toIdempotencyKey(requestId.toUpperCase())).toBeUndefined();
    expect(toIdempotencyKey(requestId.replaceAll("-", ""))).toBeUndefined();
    expect(toIdempotencyKey(`${requestId}0`)).toBeUndefined();
    expect(toIdempotencyKey(42)).toBeUndefined();
    expect(toIdempotencyKey(newIdempotencyKey())).toBeDefined();
  });
});

describe("body limits", () => {
  it("rejects a wrong or missing content type before reading", async () => {
    for (const type of ["text/plain", "application/jsonx", undefined]) {
      const headers: Record<string, string> = type === undefined ? {} : { "Content-Type": type };
      await expect(readBoundedJson(post(headers, "{}"), 100)).rejects.toMatchObject({
        reason: "unsupported_media_type"
      });
    }
  });

  it("accepts JSON with parameters and rejects a multipart request without a boundary", async () => {
    expect(
      await readBoundedJson(
        post({ "Content-Type": "Application/JSON; charset=utf-8" }, '{"a":1}'),
        100
      )
    ).toEqual({ a: 1 });
    const result = guardMutation(post({ "Content-Type": "multipart/form-data" }), {
      policy,
      requestId,
      body: { rule: "multipart", maxBytes: 100 }
    });
    // No Origin either; the wrong-content-type case is asserted with a valid Origin below.
    expect(result.ok).toBe(false);
    const withOrigin = guardMutation(
      post({ Origin: origin, "Content-Type": "multipart/form-data" }),
      { policy, requestId, body: { rule: "multipart", maxBytes: 100 } }
    );
    expect(withOrigin.ok ? 200 : withOrigin.response.status).toBe(415);
  });

  it("rejects an oversized declared length and a malformed one", async () => {
    await expect(
      readBoundedJson(
        post({ "Content-Type": "application/json", "Content-Length": "101" }, "{}"),
        100
      )
    ).rejects.toMatchObject({ reason: "payload_too_large" });
    const bad = guardMutation(
      post({ Origin: origin, "Content-Type": "application/json", "Content-Length": "abc" }),
      { policy, requestId, body: { rule: "json", maxBytes: 100 } }
    );
    expect(bad.ok ? 200 : bad.response.status).toBe(413);
  });

  it("rejects a streamed body that exceeds the cap even when Content-Length is absent", async () => {
    const chunk = new TextEncoder().encode("x".repeat(60));
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(chunk);
        controller.enqueue(chunk);
        controller.close();
      }
    });
    const request = new Request("http://10.0.0.5:3000/api/x", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: stream,
      duplex: "half"
    } as RequestInit);
    await expect(readBoundedJson(request, 100)).rejects.toBeInstanceOf(BodyRejectedError);
  });

  it("limits a raw stream and passes one within the cap", async () => {
    const make = (size: number) =>
      new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(new Uint8Array(size));
          controller.close();
        }
      });
    const ok = await new Response(limitBodyStream(make(10), 10)).arrayBuffer();
    expect(ok.byteLength).toBe(10);
    await expect(new Response(limitBodyStream(make(11), 10)).arrayBuffer()).rejects.toBeInstanceOf(
      BodyRejectedError
    );
  });

  it("returns undefined for an empty body and rejects invalid or non-UTF-8 JSON", async () => {
    expect(
      await readBoundedJson(post({ "Content-Type": "application/json" }), 100)
    ).toBeUndefined();
    expect(
      await readBoundedJson(post({ "Content-Type": "application/json" }, ""), 100)
    ).toBeUndefined();
    await expect(
      readBoundedJson(post({ "Content-Type": "application/json" }, "{nope"), 100)
    ).rejects.toMatchObject({ reason: "invalid_json" });
    await expect(
      readBoundedJson(
        post({ "Content-Type": "application/json" }, new Uint8Array([0x7b, 0xff, 0x7d])),
        100
      )
    ).rejects.toMatchObject({ reason: "invalid_json" });
  });
});

describe("guardMutation", () => {
  const jsonHeaders = { Origin: origin, "Content-Type": "application/json" };
  const base = { policy, requestId, body: { rule: "json", maxBytes: 100 } } as const;

  function status(result: ReturnType<typeof guardMutation>): number {
    return result.ok ? 200 : result.response.status;
  }

  it("passes a same-origin JSON request and reports no idempotency key", () => {
    expect(guardMutation(post(jsonHeaders, "{}"), base)).toEqual({
      ok: true,
      idempotencyKey: undefined
    });
  });

  it("checks Origin before anything else", () => {
    const result = guardMutation(post({ "Content-Type": "text/plain" }), {
      ...base,
      csrf: { presented: undefined, expected: token }
    });
    expect(status(result)).toBe(403);
    expect(result.ok ? "" : result.response.headers.get("Cache-Control")).toBe("no-store");
  });

  it("checks CSRF before reading the body and reports a generic code", async () => {
    const result = guardMutation(post(jsonHeaders, "{}"), {
      ...base,
      csrf: { presented: "B".repeat(43), expected: token }
    });
    expect(status(result)).toBe(403);
    const body = (await (result.ok ? new Response() : result.response).json()) as { code: string };
    expect(body.code).toBe("csrf_invalid");
    expect(
      guardMutation(post(jsonHeaders, "{}"), {
        ...base,
        csrf: { presented: token, expected: token }
      }).ok
    ).toBe(true);
  });

  it("requires a valid idempotency key when the operation demands one", () => {
    const options = { ...base, requireIdempotencyKey: true } as const;
    expect(status(guardMutation(post(jsonHeaders, "{}"), options))).toBe(400);
    expect(
      status(
        guardMutation(post({ ...jsonHeaders, "Idempotency-Key": "not-a-uuid" }, "{}"), options)
      )
    ).toBe(400);
    expect(
      guardMutation(post({ ...jsonHeaders, "Idempotency-Key": requestId }, "{}"), options)
    ).toEqual({ ok: true, idempotencyKey: requestId });
  });

  it("enforces an empty body for empty-body operations", () => {
    const options = { policy, requestId, body: { rule: "empty", maxBytes: 0 } } as const;
    expect(guardMutation(post({ Origin: origin }), options).ok).toBe(true);
    expect(guardMutation(post({ Origin: origin, "Content-Length": "0" }), options).ok).toBe(true);
    expect(
      status(guardMutation(post({ Origin: origin, "Content-Length": "2" }, "{}"), options))
    ).toBe(413);
    expect(
      status(guardMutation(post({ Origin: origin, "Transfer-Encoding": "chunked" }), options))
    ).toBe(413);
  });
});

describe("backend request assembly", () => {
  const credentialsInBrowserRequest = {
    Cookie: "sg_session=secret",
    Authorization: "Bearer stolen",
    Host: "evil.example",
    "X-Forwarded-For": "1.2.3.4",
    "X-Internal": "x"
  };

  it("builds only allowlisted headers from validated values, never from browser headers", () => {
    const request = post(
      { ...credentialsInBrowserRequest, "Content-Type": "application/json" },
      "{}"
    );
    expect(request.headers.get("X-Forwarded-For")).toBe("1.2.3.4");

    const { headers } = buildBackendHeaders(
      {
        context: { locale: "yo", requestId },
        contentType: "application/json",
        idempotencyKey: requestId,
        session: "s".repeat(40),
        csrf: token
      },
      () => requestId
    );

    for (const name of Object.keys(headers)) {
      expect(BACKEND_HEADER_ALLOWLIST).toContain(name.toLowerCase());
    }
    expect(headers).toMatchObject({
      "X-Request-Id": requestId,
      "X-Shaidago-Locale": "yo",
      "Content-Type": "application/json",
      "Idempotency-Key": requestId,
      "X-Shaidago-Session": "s".repeat(40),
      "X-Shaidago-Csrf": token
    });
  });

  it("drops malformed session and CSRF values and multipart types that are not multipart", () => {
    const { headers } = buildBackendHeaders(
      {
        context: {},
        multipartContentType: "text/html; boundary=x",
        session: "bad value with spaces and \r\n",
        csrf: "x"
      },
      () => requestId
    );
    expect(Object.keys(headers)).toEqual(["X-Request-Id"]);
  });

  it("forwards a multipart type with its boundary", () => {
    const { headers } = buildBackendHeaders(
      { context: {}, multipartContentType: "multipart/form-data; boundary=abc" },
      () => requestId
    );
    expect(headers["Content-Type"]).toBe("multipart/form-data; boundary=abc");
  });

  it("rejects an invalid idempotency key rather than replacing it", () => {
    expect(() =>
      buildBackendHeaders({ context: {}, idempotencyKey: "reused-or-invalid" }, () => requestId)
    ).toThrowError(BackendRequestError);
  });
});

describe("abort and timeout propagation", () => {
  it("aborts the backend signal when the client disconnects and classifies it", () => {
    const controller = new AbortController();
    const request = new Request("http://10.0.0.5:3000/api/x", { signal: controller.signal });
    const signal = backendSignal(request, 60_000);
    expect(signal.aborted).toBe(false);
    expect(classifyAbort(request)).toBe("timeout");
    controller.abort();
    expect(signal.aborted).toBe(true);
    expect(classifyAbort(request)).toBe("client_aborted");
  });

  it("aborts on timeout without a client abort", async () => {
    const request = new Request("http://10.0.0.5:3000/api/x");
    const signal = backendSignal(request, 1);
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(signal.aborted).toBe(true);
    expect(classifyAbort(request)).toBe("timeout");
  });
});

describe("browser problem responses", () => {
  async function read(response: Response) {
    return { response, body: (await response.json()) as Record<string, unknown> };
  }

  it("shapes an API problem without backend text, and always sets no-store", async () => {
    const { response, body } = await read(
      apiProblemResponse({
        status: 422,
        code: "validation_failed",
        requestId,
        fieldErrors: [{ field: "body.description", code: "too_short" }],
        retryAfterSeconds: undefined
      })
    );
    expect(response.status).toBe(422);
    expect(response.headers.get("Content-Type")).toBe("application/problem+json");
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(response.headers.get("X-Request-Id")).toBe(requestId);
    expect(body).toEqual({
      type: "about:blank",
      title: "Some details need attention",
      status: 422,
      code: "validation_failed",
      request_id: requestId,
      errors: [{ field: "body.description", code: "too_short" }]
    });
  });

  it("replaces an unsafe code and bounds Retry-After", async () => {
    const { response, body } = await read(
      problemResponse({
        status: 500,
        code: "Bad Code <script>",
        requestId,
        retryAfterSeconds: 99999
      })
    );
    expect(body["code"]).toBe("internal_error");
    expect(response.headers.get("Retry-After")).toBeNull();
    const limited = problemResponse({
      status: 429,
      code: "rate_limited",
      requestId,
      retryAfterSeconds: 7
    });
    expect(limited.headers.get("Retry-After")).toBe("7");
  });

  it("maps upstream failure, body rejection, and abort to stable codes", async () => {
    expect((await read(unavailableResponse("timeout", requestId))).body["code"]).toBe(
      "upstream_timeout"
    );
    expect(unavailableResponse("timeout", requestId).status).toBe(504);
    expect(unavailableResponse("network", requestId).status).toBe(503);
    expect(unavailableResponse("malformed_response", requestId).status).toBe(503);
    expect(bodyRejectedResponse(new BodyRejectedError("payload_too_large"), requestId).status).toBe(
      413
    );
    expect(
      bodyRejectedResponse(new BodyRejectedError("unsupported_media_type"), requestId).status
    ).toBe(415);
    expect(bodyRejectedResponse(new BodyRejectedError("invalid_json"), requestId).status).toBe(400);
    expect(abortedResponse(requestId).status).toBe(499);
  });
});
