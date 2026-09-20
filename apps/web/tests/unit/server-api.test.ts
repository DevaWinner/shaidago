import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it, vi, type Mock } from "vitest";

import { buildForwardedHeaders } from "@/lib/api/forwarded-context";
import { createServerApi, serverApi } from "@/lib/api/server";
import { ServerEnvironmentError } from "@/lib/config/server";

type Fetch = (request: Request) => Promise<Response>;

const credential = "shaida-go-unit-test-credential-not-a-secret";
const requestId = "0198f1a2-7b3c-7d4e-8f5a-123456789abc";
const problemHeaders = { "Content-Type": "application/problem+json", "Retry-After": "7" };

function problemBody(code = "not_found", status = 404) {
  return JSON.stringify({
    type: "about:blank",
    title: "Backend title with secret-looking detail",
    status,
    code,
    detail: "internal detail must never surface",
    request_id: "not-trusted"
  });
}

function build(fetchImpl: Mock<Fetch>) {
  const sleep = vi.fn<(milliseconds: number) => Promise<void>>(async () => undefined);

  return {
    sleep,
    api: createServerApi({
      environment: {
        appEnvironment: "test",
        apiInternalUrl: "http://api.internal-test.invalid",
        internalWebCredential: credential,
        clientHmacKey: undefined,
        trustedProxyHops: 1
      },
      fetch: fetchImpl as unknown as typeof fetch,
      sleep,
      generateRequestId: () => requestId
    })
  };
}

function requestAt(mock: Mock<Fetch>, index: number): Request {
  const request = mock.mock.calls[index]?.[0];

  if (request === undefined) {
    throw new Error("expected a recorded request");
  }

  return request;
}

const json = (body: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json", ETag: '"abc"' },
    ...init
  });

describe("server API client", () => {
  it("authenticates as the web caller and forwards only validated context", async () => {
    const fetchImpl = vi.fn<Fetch>(async () => json({ items: [] }));
    const { api } = build(fetchImpl);

    const result = await api.getLocalities({
      locale: "ha",
      requestId: "not-a-uuid",
      clientHmac: "f".repeat(64)
    });

    const request = requestAt(fetchImpl, 0);
    expect(request.url).toBe("http://api.internal-test.invalid/v1/localities");
    expect(request.headers.get("Authorization")).toBe(`Bearer web.${credential}`);
    expect(request.headers.get("X-Request-Id")).toBe(requestId);
    expect(request.headers.get("X-Shaidago-Locale")).toBe("ha");
    expect(request.headers.get("X-Shaidago-Client-Hmac")).toBe("f".repeat(64));
    expect(request.headers.get("Cookie")).toBeNull();
    expect(result).toEqual({
      kind: "ok",
      status: 200,
      data: { items: [] },
      etag: '"abc"',
      replayed: false,
      requestId
    });
  });

  it("drops invalid locale, HMAC, and entity tags instead of forwarding them", async () => {
    const fetchImpl = vi.fn<Fetch>(async () => json({ items: [] }));
    const { api } = build(fetchImpl);

    await api.getLocalities({
      locale: "fr",
      clientHmac: "nope",
      ifNoneMatch: '"ok"\r\nX-Injected: 1'
    });

    const request = requestAt(fetchImpl, 0);
    expect(request.headers.get("X-Shaidago-Locale")).toBeNull();
    expect(request.headers.get("X-Shaidago-Client-Hmac")).toBeNull();
    expect(request.headers.get("If-None-Match")).toBeNull();
    expect(request.headers.get("X-Injected")).toBeNull();
  });

  it("serialises typed filters and path values, and keeps a 304 distinct from empty data", async () => {
    const fetchImpl = vi.fn<Fetch>(
      async () => new Response(null, { status: 304, headers: { ETag: '"v1"' } })
    );
    const { api } = build(fetchImpl);

    const result = await api.listProjects(
      { locality: "amac", q: "school", limit: 20 },
      { ifNoneMatch: '"v1"' }
    );

    const request = requestAt(fetchImpl, 0);
    expect(new URL(request.url).search).toBe("?locality=amac&q=school&limit=20");
    expect(request.headers.get("If-None-Match")).toBe('"v1"');
    expect(result).toEqual({ kind: "not_modified", etag: '"v1"', requestId });

    await api.getProject("a b/c");
    expect(requestAt(fetchImpl, 1).url).toContain("/v1/projects/a%20b%2Fc");
  });

  it("maps a problem by code and never exposes backend title, detail, or request ID", async () => {
    const fetchImpl = vi.fn<Fetch>(
      async () =>
        new Response(problemBody("rate_limited", 429), { status: 429, headers: problemHeaders })
    );
    const { api, sleep } = build(fetchImpl);

    const result = await api.getProject("x");

    expect(result).toEqual({
      kind: "problem",
      problem: {
        status: 429,
        code: "rate_limited",
        requestId,
        fieldErrors: [],
        retryAfterSeconds: 7
      }
    });
    expect(JSON.stringify(result)).not.toContain("internal detail");
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(sleep).not.toHaveBeenCalled();
  });

  it("does not retry a non-transient problem", async () => {
    const fetchImpl = vi.fn<Fetch>(
      async () =>
        new Response(problemBody("not_found"), {
          status: 404,
          headers: { "Content-Type": "application/problem+json" }
        })
    );
    const { api } = build(fetchImpl);

    const result = await api.getProject("x");

    expect(result.kind).toBe("problem");
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it("retries a read once after a transient 503 and succeeds", async () => {
    const fetchImpl = vi
      .fn<Fetch>()
      .mockResolvedValueOnce(
        new Response(problemBody("dependency_unavailable", 503), { status: 503 })
      )
      .mockResolvedValueOnce(json({ items: [] }));
    const { api, sleep } = build(fetchImpl);

    const result = await api.getLocalities();

    expect(result.kind).toBe("ok");
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(sleep).toHaveBeenCalledOnce();
  });

  it("does not retry a 503 that asks for a long wait and bounds retries to one", async () => {
    const longWait = vi.fn<Fetch>(
      async () =>
        new Response(problemBody("dependency_unavailable", 503), {
          status: 503,
          headers: { "Retry-After": "30" }
        })
    );
    expect((await build(longWait).api.getLocalities()).kind).toBe("problem");
    expect(longWait).toHaveBeenCalledTimes(1);

    const always503 = vi.fn<Fetch>(
      async () => new Response(problemBody("dependency_unavailable", 503), { status: 503 })
    );
    expect((await build(always503).api.getLocalities()).kind).toBe("problem");
    expect(always503).toHaveBeenCalledTimes(2);
  });

  it("reports unavailability for network failure, timeout, and non-problem error bodies", async () => {
    const network = vi.fn<Fetch>(async () => {
      throw new TypeError("fetch failed: secret-host.internal");
    });
    const networkResult = await build(network).api.getLocalities();
    expect(networkResult).toEqual({ kind: "unavailable", reason: "network", requestId });
    expect(network).toHaveBeenCalledTimes(2);
    expect(JSON.stringify(networkResult)).not.toContain("secret-host");

    const timeout = vi.fn<Fetch>(async () => {
      throw new DOMException("timed out", "TimeoutError");
    });
    expect(await build(timeout).api.getLocalities()).toEqual({
      kind: "unavailable",
      reason: "timeout",
      requestId
    });
    expect(timeout).toHaveBeenCalledTimes(1);

    const html = vi.fn<Fetch>(
      async () => new Response("<html>bad gateway</html>", { status: 502 })
    );
    expect(await build(html).api.getLocalities()).toEqual({
      kind: "unavailable",
      reason: "malformed_response",
      requestId
    });

    const badJson = vi.fn<Fetch>(
      async () =>
        new Response("{not json", { status: 200, headers: { "Content-Type": "application/json" } })
    );
    expect((await build(badJson).api.getLocalities()).kind).toBe("unavailable");
  });

  it("reads an approved source by opaque project and source identifiers", async () => {
    const fetchImpl = vi.fn<Fetch>(async () => json({ source: {}, excerpts: [] }));

    await build(fetchImpl).api.getProjectSource("clinic", "0198f1a2-7b3c-7d4e-8f5a-123456789abc");

    expect(requestAt(fetchImpl, 0).url).toBe(
      "http://api.internal-test.invalid/v1/projects/clinic/sources/0198f1a2-7b3c-7d4e-8f5a-123456789abc"
    );
  });

  it("builds from runtime environment on first use and fails closed when it is invalid", async () => {
    vi.stubEnv("APP_ENV", "test");
    vi.stubEnv("API_INTERNAL_URL", "http://api.internal-test.invalid");
    vi.stubEnv("INTERNAL_WEB_CREDENTIAL_CURRENT", credential);
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(json({ items: [] }));
    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");

    expect((await serverApi().getLocalities()).kind).toBe("ok");
    expect(fetchSpy).toHaveBeenCalledOnce();
    expect(setTimeoutSpy).not.toHaveBeenCalled();

    vi.stubEnv("API_INTERNAL_URL", "");
    expect(() => serverApi()).toThrowError(ServerEnvironmentError);
    vi.unstubAllEnvs();
  });

  it("waits with a real timer between read attempts", async () => {
    vi.stubEnv("APP_ENV", "test");
    vi.stubEnv("API_INTERNAL_URL", "http://api.internal-test.invalid");
    vi.stubEnv("INTERNAL_WEB_CREDENTIAL_CURRENT", credential);
    vi.spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new TypeError("down"))
      .mockResolvedValueOnce(json({ items: [] }));

    expect((await serverApi().getLocalities()).kind).toBe("ok");
    vi.unstubAllEnvs();
  });

  it("carries field error codes without values", async () => {
    const body = JSON.stringify({
      type: "about:blank",
      title: "t",
      status: 422,
      code: "validation_failed",
      detail: "d",
      errors: [{ field: "query.limit", code: "less_than_equal" }]
    });
    const fetchImpl = vi.fn<Fetch>(async () => new Response(body, { status: 422 }));
    const result = await build(fetchImpl).api.listProjects({ limit: 999 });

    expect(result).toMatchObject({
      kind: "problem",
      problem: { fieldErrors: [{ field: "query.limit", code: "less_than_equal" }] }
    });
  });

  it("keeps a valid request ID and replaces a malformed one", () => {
    const generated = () => requestId;
    expect(
      buildForwardedHeaders({ requestId: "AAAAAAAA-BBBB-4CCC-8DDD-EEEEEEEEEEEE" }, generated)
        .requestId
    ).toBe("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee");
    expect(buildForwardedHeaders({ requestId: "x\r\ny" }, generated).requestId).toBe(requestId);
  });
});

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);

    if (statSync(path).isDirectory()) {
      return sourceFiles(path);
    }

    return /\.(ts|tsx)$/.test(name) ? [path] : [];
  });
}

describe("client/server boundary", () => {
  const root = join(import.meta.dirname, "..", "..");
  const files = [...sourceFiles(join(root, "src")), ...sourceFiles(join(root, "app"))];

  it("keeps server-only modules marked", () => {
    for (const file of ["src/lib/api/server.ts", "src/lib/config/server.ts"]) {
      expect(readFileSync(join(root, file), "utf8")).toMatch(/^import "server-only";/);
    }
  });

  it("never imports server modules from a client component or the generated client's callers", () => {
    const offenders = files
      .filter((file) => /^\s*["']use client["']/.test(readFileSync(file, "utf8")))
      .filter((file) =>
        /from\s+["']@\/lib\/(?:api\/server|config\/server|api\/generated\/client)["']/.test(
          readFileSync(file, "utf8")
        )
      )
      .map((file) => relative(root, file));

    expect(offenders).toEqual([]);
  });

  it("does not log from the API transport", () => {
    expect(readFileSync(join(root, "src/lib/api/server.ts"), "utf8")).not.toMatch(/console\./);
  });
});
