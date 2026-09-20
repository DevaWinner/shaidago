import { describe, expect, it } from "vitest";

import en from "../../messages/en.json";
import { formatMessage } from "@/i18n/catalogue";
import { BFF_PROBLEM_CODES } from "@/lib/bff/problem";
import { networkProblem, readBrowserProblem } from "@/lib/problems/browser-problem";
import {
  PROBLEM_CODE_KEYS,
  describeProblem,
  mapFieldErrors,
  preservedValues,
  ruleMessage,
  type SafeProblem
} from "@/lib/problems/problem-messages";

const copy = en.problems;
const format = (template: string, values: Readonly<Record<string, string | number>>) =>
  formatMessage("en", template, values);
const requestId = "0198f1a2-7b3c-4d4e-8f5a-123456789abc";

const problem = (overrides: Partial<SafeProblem> = {}): SafeProblem => ({
  code: "validation_failed",
  status: 422,
  requestId,
  retryAfterSeconds: undefined,
  fieldErrors: [],
  ...overrides
});

describe("code coverage", () => {
  it("maps every code the BFF can return", () => {
    for (const code of BFF_PROBLEM_CODES) {
      expect(Object.hasOwn(PROBLEM_CODE_KEYS, code), code).toBe(true);
    }
    expect(Object.hasOwn(PROBLEM_CODE_KEYS, "network_unavailable")).toBe(true);
  });

  it("maps every documented API code", () => {
    for (const code of [
      "bad_request",
      "unauthenticated",
      "forbidden",
      "not_found",
      "method_not_allowed",
      "conflict",
      "payload_too_large",
      "unsupported_media_type",
      "validation_failed",
      "rate_limited",
      "internal_error",
      "dependency_unavailable",
      "invalid_cursor",
      "invalid_credentials",
      "csrf_invalid",
      "tracking_code_not_recognised",
      "invalid_reporter_credentials",
      "idempotency_conflict",
      "report_version_conflict",
      "report_status_transition_not_allowed",
      "markup_not_allowed",
      "preview_stale",
      "public_update_report_not_verified",
      "public_update_not_draft",
      "publication_incomplete",
      "query_changed"
    ]) {
      expect(Object.hasOwn(PROBLEM_CODE_KEYS, code), code).toBe(true);
    }
  });

  it("uses every message and every message exists, so no copy is dead and none is missing", () => {
    const used = new Set<string>(Object.values(PROBLEM_CODE_KEYS));
    const defined = Object.keys(copy.codes).filter((key) => key !== "unknown");

    expect([...used].toSorted()).toEqual(defined.toSorted());
  });
});

describe("describeProblem", () => {
  it("chooses copy only from the code and shows no reference for an ordinary problem", () => {
    const view = describeProblem(problem({ code: "rate_limited", status: 429 }), copy, format);

    expect(view.message).toBe(copy.codes.rateLimited);
    expect(view).toMatchObject({
      isGeneric: false,
      referenceLine: undefined,
      retryHint: undefined
    });
  });

  it("gives an unknown code the generic message with the support reference", () => {
    const view = describeProblem(problem({ code: "some_new_backend_code" }), copy, format);

    expect(view.message).toBe(copy.codes.unknown);
    expect(view.isGeneric).toBe(true);
    expect(view.referenceLine).toBe(`Support reference: ${requestId}`);
    expect(
      describeProblem(problem({ code: "internal_error", status: 500 }), copy, format).referenceLine
    ).toBe(`Support reference: ${requestId}`);
  });

  it("does not treat inherited object keys as known codes", () => {
    for (const code of ["constructor", "__proto__", "toString", "hasOwnProperty"]) {
      const view = describeProblem(problem({ code }), copy, format);

      expect(view.isGeneric, code).toBe(true);
      expect(view.message, code).toBe(copy.codes.unknown);
    }
  });

  it("formats Retry-After with plural rules and warns about unknown completion only for mutations", () => {
    expect(
      describeProblem(problem({ code: "rate_limited", retryAfterSeconds: 1 }), copy, format)
        .retryHint
    ).toBe("Try again in 1 second.");
    expect(
      describeProblem(problem({ code: "rate_limited", retryAfterSeconds: 12 }), copy, format)
        .retryHint
    ).toBe("Try again in 12 seconds.");
    const timeout = problem({ code: "upstream_timeout", status: 504 });

    expect(describeProblem(timeout, copy, format, { mutation: true }).mayHaveCompletedHint).toBe(
      copy.mayHaveCompleted
    );
    expect(describeProblem(timeout, copy, format).mayHaveCompletedHint).toBeUndefined();
    expect(
      describeProblem(problem({ code: "forbidden", status: 403 }), copy, format, { mutation: true })
        .mayHaveCompletedHint
    ).toBeUndefined();
  });

  it("turns field rule codes into reviewed sentences and never echoes the code", () => {
    const view = describeProblem(
      problem({
        fieldErrors: [
          { field: "body.description", code: "string_too_short" },
          { field: "body.project_slug", code: "missing" },
          { field: "body.x", code: "something_new" }
        ]
      }),
      copy,
      format
    );

    expect(view.fieldErrors.map((error) => error.message)).toEqual([
      copy.rules.tooShort,
      copy.rules.required,
      copy.rules.invalid
    ]);
    for (const rule of [
      "too_small",
      "too_big",
      "invalid_type",
      "extra_forbidden",
      "markup_not_allowed",
      "constructor"
    ]) {
      expect(ruleMessage(rule, copy)).not.toContain(rule);
    }
  });
});

describe("mapFieldErrors and preservedValues", () => {
  const errors = [
    { field: "body.description", message: "too short" },
    { field: "description", message: "second message for the same control" },
    { field: "query.limit", message: "not a control" },
    { field: "body.constructor", message: "hostile" }
  ];

  it("maps paths to control ids once each and keeps unmapped messages visible", () => {
    const { mapped, unmapped } = mapFieldErrors(errors, { description: "report-description" });

    expect(mapped).toEqual([{ controlId: "report-description", message: "too short" }]);
    expect(unmapped).toEqual(["not a control", "hostile"]);
  });

  it("re-fills non-secret values and never restores secrets, contacts, or files", () => {
    const file = new File(["x"], "evidence.png");
    const kept = preservedValues(
      {
        description: "kept",
        concern: "other",
        contact_value: "a@b.example",
        passphrase: "six words",
        attachments: file
      },
      ["contact_value", "passphrase"]
    );

    expect(kept).toEqual({ description: "kept", concern: "other" });
  });
});

describe("readBrowserProblem", () => {
  const problemResponse = (body: unknown, status: number, headers: Record<string, string> = {}) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/problem+json", ...headers }
    });

  it("reads only the code, request id, field rules, and Retry-After", async () => {
    const view = await readBrowserProblem(
      problemResponse(
        {
          type: "about:blank",
          title: "Backend title with 10.0.0.9",
          detail: "secret backend detail",
          status: 429,
          code: "rate_limited",
          request_id: requestId,
          errors: [{ field: "body.code", code: "string_too_short", value: "SECRET-VALUE" }]
        },
        429,
        { "Retry-After": "7" }
      )
    );

    expect(view).toEqual({
      code: "rate_limited",
      status: 429,
      requestId,
      retryAfterSeconds: 7,
      fieldErrors: [{ field: "body.code", code: "string_too_short" }]
    });
    expect(JSON.stringify(view)).not.toMatch(/10\.0\.0\.9|secret|SECRET/);
  });

  it("treats a wrong content type, malformed JSON, or a bad shape as an internal error", async () => {
    for (const response of [
      new Response("<html>bad gateway</html>", { status: 502 }),
      new Response("{not json", {
        status: 500,
        headers: { "Content-Type": "application/problem+json" }
      }),
      problemResponse({ code: "Bad Code!" }, 500),
      problemResponse({ code: "ok", errors: "nope" }, 500),
      problemResponse({ nothing: true }, 500)
    ]) {
      expect((await readBrowserProblem(response)).code).toBe("internal_error");
    }
  });

  it("falls back to the response request-id header and ignores an unsafe one or a bad Retry-After", async () => {
    const response = new Response("x", {
      status: 500,
      headers: { "X-Request-Id": requestId, "Retry-After": "soon" }
    });

    expect(await readBrowserProblem(response)).toMatchObject({
      requestId,
      retryAfterSeconds: undefined
    });
    expect(
      (
        await readBrowserProblem(
          problemResponse({ code: "not_found", request_id: "<script>" }, 404)
        )
      ).code
    ).toBe("internal_error");
  });

  it("describes a lost connection without any response", () => {
    expect(networkProblem()).toMatchObject({ code: "network_unavailable", fieldErrors: [] });
    expect(describeProblem(networkProblem(), copy, format, { mutation: true })).toMatchObject({
      message: copy.codes.network,
      mayHaveCompletedHint: copy.mayHaveCompleted
    });
  });
});
