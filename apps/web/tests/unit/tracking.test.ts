import { afterEach, describe, expect, it, vi } from "vitest";

import {
  parseAck,
  parseHandleCreated,
  parseHandleReports,
  parseStatus,
  postJson
} from "@/lib/tracking/client";
import { CODE_MAX, normaliseCode } from "@/lib/tracking/normalise";

const uuid = "0198f1a2-7b3c-4d4e-8f5a-123456789abc";
const status = {
  follow_up_questions: [{ question_id: uuid, state: "open", text: "When?" }],
  message: "Hello",
  next_action: "answer_follow_up",
  status: "needs_information",
  status_updated_at: "2026-09-19T09:00:00Z"
};

describe("normaliseCode", () => {
  it("removes whitespace and zero-width characters and unifies dashes, without touching letters or digits", () => {
    expect(normaliseCode("  sg – demo‑ 0001\n")).toBe("sg-demo-0001");
    expect(normaliseCode("SG​-DEMO﻿-0001")).toBe("SG-DEMO-0001");
    expect(normaliseCode("ＳＧ-１２")).toBe("SG-12");
    expect(normaliseCode("aB3-x")).toBe("aB3-x");
    expect(normaliseCode("   ")).toBe("");
    expect(CODE_MAX).toBe(256);
  });
});

describe("parseStatus", () => {
  it("accepts the documented shape", () => {
    expect(parseStatus(status)).toEqual({
      status: "needs_information",
      updatedAt: "2026-09-19T09:00:00Z",
      message: "Hello",
      nextAction: "answer_follow_up",
      questions: [{ id: uuid, text: "When?", state: "open" }]
    });
  });

  it.each([
    ["a non-object", 5],
    ["an unknown status", { ...status, status: "guilty" }],
    ["an unknown next action", { ...status, next_action: "arrest" }],
    ["a bad date", { ...status, status_updated_at: "soon" }],
    ["a long message", { ...status, message: "x".repeat(2001) }],
    [
      "too many questions",
      { ...status, follow_up_questions: Array(6).fill(status.follow_up_questions[0]) }
    ],
    [
      "a malformed question",
      { ...status, follow_up_questions: [{ question_id: "x", state: "open", text: "t" }] }
    ],
    [
      "a bad question state",
      { ...status, follow_up_questions: [{ question_id: uuid, state: "maybe", text: "t" }] }
    ],
    ["no questions list", { ...status, follow_up_questions: null }]
  ])("rejects %s", (_name, value) => {
    expect(parseStatus(value)).toBeUndefined();
  });
});

describe("other parsers", () => {
  it("parses a handle report list, tolerating an unknown next action", () => {
    const item = {
      message: "m",
      next_action: "something_new",
      status: "received",
      status_updated_at: status.status_updated_at
    };

    expect(parseHandleReports({ reports: [item] })).toEqual([
      {
        status: "received",
        updatedAt: status.status_updated_at,
        message: "m",
        nextAction: undefined
      }
    ]);
    expect(parseHandleReports({ reports: [] })).toEqual([]);
    expect(parseHandleReports({ reports: [{ ...item, status: "x" }] })).toBeUndefined();
    expect(parseHandleReports({ reports: Array(201).fill(item) })).toBeUndefined();
    expect(parseHandleReports({})).toBeUndefined();
  });

  it("parses one-time credentials only when they are marked unrecoverable", () => {
    expect(parseHandleCreated({ handle: "h", passphrase: "p", recoverable: false })).toEqual({
      handle: "h",
      passphrase: "p"
    });
    expect(parseHandleCreated({ handle: "h", passphrase: "p", recoverable: true })).toBeUndefined();
    expect(parseHandleCreated({ handle: "", passphrase: "p", recoverable: false })).toBeUndefined();
    expect(parseHandleCreated(null)).toBeUndefined();
  });

  it("parses an acknowledgement", () => {
    expect(parseAck({ acknowledged: true, question_state: "skipped" })).toBe("skipped");
    expect(parseAck({ acknowledged: false, question_state: "skipped" })).toBeUndefined();
    expect(parseAck({ acknowledged: true, question_state: "open" })).toBeUndefined();
  });
});

describe("postJson", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends only a JSON body with the locale, never a credential in the address, and stores nothing", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ ok: 1 }), { status: 200 }));

    vi.stubGlobal("fetch", fetcher);
    const outcome = await postJson(
      "/api/tracking/lookup",
      { code: "SECRET-CODE" },
      { locale: "yo", idempotencyKey: "k" }
    );
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe("/api/tracking/lookup");
    expect(url).not.toContain("SECRET");
    expect(init.cache).toBe("no-store");
    expect(JSON.parse(String(init.body))).toEqual({ code: "SECRET-CODE" });
    expect(init.headers).toMatchObject({ "X-Shaidago-Locale": "yo", "Idempotency-Key": "k" });
    expect(outcome).toMatchObject({ kind: "ok", status: 200, data: { ok: 1 }, replayed: false });
  });

  it("sends no body and no content type for an empty request, and reads a 204", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));

    vi.stubGlobal("fetch", fetcher);
    expect(await postJson("/x", undefined, { locale: "en" })).toMatchObject({
      kind: "ok",
      status: 204,
      data: undefined
    });
    const init = fetcher.mock.calls[0]?.[1] as RequestInit;

    expect(init.body).toBeNull();
    expect(init.headers).not.toHaveProperty("Content-Type");
  });

  it("classifies a problem, a replay, an unreadable body, a network loss, and an abort", async () => {
    const replay = new Response("{}", { status: 200, headers: { "Idempotency-Replayed": "true" } });
    const problem = new Response(JSON.stringify({ code: "rate_limited" }), {
      status: 429,
      headers: { "Content-Type": "application/problem+json", "Retry-After": "12" }
    });
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(replay)
      .mockResolvedValueOnce(problem)
      .mockResolvedValueOnce(new Response("not json", { status: 200 }))
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockRejectedValueOnce(new DOMException("aborted", "AbortError"));

    vi.stubGlobal("fetch", fetcher);
    expect(await postJson("/x", {}, { locale: "en" })).toMatchObject({
      kind: "ok",
      replayed: true
    });
    expect(await postJson("/x", {}, { locale: "en" })).toMatchObject({
      kind: "problem",
      problem: { code: "rate_limited", retryAfterSeconds: 12 }
    });
    expect(await postJson("/x", {}, { locale: "en" })).toMatchObject({
      kind: "problem",
      problem: { code: "internal_error" }
    });
    expect(await postJson("/x", {}, { locale: "en" })).toEqual({ kind: "network" });
    expect(await postJson("/x", {}, { locale: "en" })).toEqual({ kind: "aborted" });
  });
});
