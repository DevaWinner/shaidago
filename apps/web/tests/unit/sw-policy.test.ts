import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

type Policy = {
  CACHES: Record<string, string>;
  LIMITS: Record<string, number>;
  classify: (url: URL, request: unknown, origin: string) => "page" | "asset" | "none";
  storable: (response: unknown, kind: string) => boolean;
  ageMs: (response: unknown, now: number) => number;
  offlinePath: (pathname: string) => string;
  localeOf: (pathname: string) => string;
  isCurrentCache: (name: string) => boolean;
};

// The worker loads this file with importScripts, which defines `self.SG_POLICY`; run it the same way.
const scope: { SG_POLICY?: Policy } = {};

new Function(
  "self",
  readFileSync(join(import.meta.dirname, "..", "..", "public", "sw-policy.js"), "utf8")
)(scope);
const policy = scope.SG_POLICY as Policy;
const ORIGIN = "https://shaidago.test";
const UUID = "0198f1a2-7b3c-4d4e-8f5a-123456789abc";

const request = (over: Record<string, unknown> = {}) => ({
  method: "GET",
  mode: "navigate",
  headers: new Headers(),
  ...over
});
const kind = (path: string, req: unknown = request(), origin = ORIGIN) =>
  policy.classify(new URL(path, ORIGIN), req, origin);
const response = (
  over: {
    status?: number;
    headers?: Record<string, string>;
    type?: string;
    redirected?: boolean;
  } = {}
) => ({
  status: over.status ?? 200,
  type: over.type ?? "basic",
  redirected: over.redirected ?? false,
  headers: new Headers({ "content-type": "text/html; charset=utf-8", ...over.headers })
});

describe("classify", () => {
  it.each([
    "/en",
    "/ha/projects",
    "/ig/projects?locality=amac&category=health&status=planned&verification=corroborated",
    "/yo/projects/synthetic-record-full",
    `/en/projects/synthetic-record-full/sources/${UUID}`,
    "/en/trust",
    "/en/offline"
  ])("stores the public page %s", (path) => {
    expect(kind(path)).toBe("page");
  });

  it.each([
    "/api/public/questions",
    "/api/reviewer/session",
    "/en/report",
    "/en/report/synthetic-record-full",
    "/en/report/complete",
    "/en/track",
    "/en/handle",
    "/en/reviewer/sign-in",
    "/en/reviewer/reports",
    `/en/reviewer/reports/${UUID}`,
    "/en/projects?q=free+text",
    "/en/projects?token=abc",
    "/en/projects?cursor=" + "x".repeat(600),
    "/de/projects",
    "/en/projects/Bad_Slug",
    "/en/projects/a/b/c",
    "/manifest.webmanifest",
    "/robots.txt"
  ])("never stores %s", (path) => {
    expect(kind(path)).toBe("none");
  });

  it("ignores everything that is not a same-origin plain GET navigation", () => {
    expect(kind("/en/projects", request({ method: "POST" }))).toBe("none");
    expect(kind("/en/projects", request({ mode: "cors" }))).toBe("none");
    expect(kind("/en/projects", request({ mode: "same-origin" }))).toBe("none");
    expect(kind("/en/projects", request(), "https://other.test")).toBe("none");
    expect(kind("/en/projects", request({ headers: new Headers({ rsc: "1" }) }))).toBe("none");
    expect(kind("/en/projects?_rsc=abc")).toBe("none");
    expect(policy.classify(new URL("https://u:p@shaidago.test/en"), request(), ORIGIN)).toBe(
      "none"
    );
  });

  it("stores only immutable framework files without a query", () => {
    const asset = request({ mode: "no-cors" });

    expect(kind("/_next/static/chunks/app-abc.js", asset)).toBe("asset");
    expect(kind("/_next/static/chunks/app-abc.js?v=1", asset)).toBe("none");
    expect(kind("/_next/image?url=x", asset)).toBe("none");
    expect(kind("/_next/data/build/en.json", asset)).toBe("none");
  });
});

describe("storable", () => {
  it("accepts a plain successful public page and an asset of any type", () => {
    expect(policy.storable(response(), "page")).toBe(true);
    expect(
      policy.storable(response({ headers: { "content-type": "text/javascript" } }), "asset")
    ).toBe(true);
    expect(
      policy.storable(
        response({ headers: { "cache-control": "public, max-age=0, must-revalidate" } }),
        "page"
      )
    ).toBe(true);
  });

  it.each([
    ["no-store", { "cache-control": "no-store" }],
    ["private", { "cache-control": "private, no-cache" }],
    ["mixed case", { "cache-control": "Public, NO-STORE" }],
    ["a cookie", { "set-cookie": "sg_session=x" }],
    ["credentials", { authorization: "Bearer x" }],
    ["json for a page", { "content-type": "application/json" }],
    ["a huge body", { "content-length": String(policy.LIMITS["maxBytes"]! + 1) }]
  ])("refuses a response with %s", (_name, headers) => {
    expect(policy.storable(response({ headers }), "page")).toBe(false);
  });

  it("refuses failures, redirects, and opaque or cross-origin responses", () => {
    expect(policy.storable(response({ status: 404 }), "page")).toBe(false);
    expect(policy.storable(response({ status: 503 }), "page")).toBe(false);
    expect(policy.storable(response({ redirected: true }), "page")).toBe(false);
    expect(policy.storable(response({ type: "opaque" }), "page")).toBe(false);
    expect(policy.storable(response({ type: "cors" }), "asset")).toBe(true);
    expect(policy.storable(undefined, "page")).toBe(false);
  });
});

describe("age, locale, and versioned caches", () => {
  it("measures the age of a saved copy and treats an unstamped one as too old", () => {
    const stamped = response({ headers: { "x-sg-saved-at": "1000" } });

    expect(policy.ageMs(stamped, 4000)).toBe(3000);
    expect(policy.ageMs(response(), 4000)).toBe(Infinity);
    expect(policy.ageMs(response({ headers: { "x-sg-saved-at": "junk" } }), 4000)).toBe(Infinity);
  });

  it("falls back to the offline page of the visitor's language, or English", () => {
    expect(policy.offlinePath("/yo/projects/x")).toBe("/yo/offline");
    expect(policy.offlinePath("/xx/projects")).toBe("/en/offline");
    expect(policy.localeOf("/ha")).toBe("ha");
  });

  it("knows its own cache names, so older versions can be deleted and nothing else is touched", () => {
    for (const name of Object.values(policy.CACHES)) expect(policy.isCurrentCache(name)).toBe(true);
    expect(policy.isCurrentCache("sg-pages-v0")).toBe(false);
    expect(policy.isCurrentCache("someone-elses-cache")).toBe(false);
    expect(Object.values(policy.CACHES).every((name) => /^sg-[a-z]+-v\d+$/.test(name))).toBe(true);
    expect(policy.LIMITS["pageEntries"]).toBeLessThanOrEqual(50);
    expect(policy.LIMITS["freshMs"]).toBeLessThan(policy.LIMITS["maxAgeMs"]!);
  });
});
