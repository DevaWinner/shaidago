import { describe, expect, it } from "vitest";

import {
  DISCOVERY_STATUSES,
  POLL_DELAYS_MS,
  RUN_MEMORY_POLICY,
  allowedDiscoveryActions,
  isDiscoveryStatus,
  isNewerRunSnapshot,
  nextPollDelayMs,
  shouldPoll
} from "@/lib/discovery/run-state";

describe("discovery run state", () => {
  it("models only the seven discovery states in the generated contract", () => {
    expect(DISCOVERY_STATUSES).toEqual([
      "queued",
      "searching",
      "analysing",
      "needs_review",
      "complete",
      "failed",
      "cancelled"
    ]);
    expect(isDiscoveryStatus("complete")).toBe(true);
    expect(isDiscoveryStatus("published")).toBe(false);
  });

  it("keeps the public run observable through needs_review but stops reviewer polling there", () => {
    for (const status of DISCOVERY_STATUSES) {
      expect(shouldPoll("public", status)).toBe(
        !["complete", "failed", "cancelled"].includes(status)
      );
      expect(shouldPoll("reviewer", status)).toBe(
        !["needs_review", "complete", "failed", "cancelled"].includes(status)
      );
    }
    expect(shouldPoll("public", "unknown")).toBe(false);
    expect(shouldPoll("reviewer", "unknown")).toBe(false);
  });

  it("does not invent public cancellation or unlock an action for an unknown state", () => {
    expect(allowedDiscoveryActions("public", "searching", false)).toEqual(["poll"]);
    expect(allowedDiscoveryActions("reviewer", "queued", false)).toEqual(["poll", "cancel"]);
    expect(allowedDiscoveryActions("reviewer", "queued", true)).toEqual(["poll"]);
    expect(allowedDiscoveryActions("reviewer", "needs_review", false)).toEqual(["review"]);
    expect(allowedDiscoveryActions("public", "needs_review", false)).toEqual([]);
    expect(allowedDiscoveryActions("reviewer", "complete", false)).toEqual([]);
    expect(allowedDiscoveryActions("public", "unknown", false)).toEqual([]);
  });

  it("uses bounded backoff unless the API supplies a valid Retry-After", () => {
    expect(POLL_DELAYS_MS).toEqual([2_000, 3_000, 5_000, 8_000, 10_000]);
    expect(nextPollDelayMs(0)).toBe(2_000);
    expect(nextPollDelayMs(1)).toBe(3_000);
    expect(nextPollDelayMs(2)).toBe(5_000);
    expect(nextPollDelayMs(3)).toBe(8_000);
    expect(nextPollDelayMs(4)).toBe(10_000);
    expect(nextPollDelayMs(40)).toBe(10_000);
    expect(nextPollDelayMs(-1)).toBe(2_000);
    expect(nextPollDelayMs(0.5)).toBe(2_000);
    expect(nextPollDelayMs(1, 30)).toBe(30_000);
    expect(nextPollDelayMs(1, 0)).toBe(3_000);
    expect(nextPollDelayMs(1, 0.5)).toBe(3_000);
  });

  it("accepts only a newer snapshot for the same run in the same scope", () => {
    const current = { scope: "reviewer" as const, runId: "run-a", version: 3 };

    expect(isNewerRunSnapshot(current, { ...current, version: 4 })).toBe(true);
    expect(isNewerRunSnapshot(current, { ...current, version: 3 })).toBe(false);
    expect(isNewerRunSnapshot(current, { ...current, version: 2 })).toBe(false);
    expect(isNewerRunSnapshot(current, { ...current, scope: "public" })).toBe(false);
    expect(isNewerRunSnapshot(current, { ...current, runId: "run-b", version: 4 })).toBe(false);
    expect(isNewerRunSnapshot(current, { ...current, version: 3.5 })).toBe(false);
  });

  it("keeps both scopes no-store and current-surface memory only", () => {
    expect(RUN_MEMORY_POLICY.public).toEqual({
      cacheControl: "no-store",
      persistence: "never",
      resume: "current-surface-memory-only"
    });
    expect(RUN_MEMORY_POLICY.reviewer).toEqual(RUN_MEMORY_POLICY.public);
  });
});
