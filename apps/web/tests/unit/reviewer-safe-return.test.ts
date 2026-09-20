import { describe, expect, it } from "vitest";

import {
  queuePath,
  safeReviewerTarget,
  signInPath,
  toSignInReason
} from "@/lib/reviewer/safe-return";

const id = "0198f1a2-7b3c-4d4e-8f5a-123456789abc";

describe("safeReviewerTarget", () => {
  it("accepts this locale's queue and one report in it", () => {
    expect(safeReviewerTarget("en", "/en/reviewer/reports")).toBe("/en/reviewer/reports");
    expect(safeReviewerTarget("ha", `/ha/reviewer/reports/${id}`)).toBe(
      `/ha/reviewer/reports/${id}`
    );
    expect(safeReviewerTarget("en", `/en/reviewer/reports/${id.toUpperCase()}`)).toBe(
      `/en/reviewer/reports/${id}`
    );
  });

  it.each([
    "https://evil.example/en/reviewer/reports",
    "//evil.example/en/reviewer/reports",
    "/\\evil.example",
    "/en/reviewer/reports?next=//evil.example",
    "/en/reviewer/reports#fragment",
    "/en/reviewer/reports/",
    "/en/reviewer/reports/not-an-id",
    `/en/reviewer/reports/${id}/../../x`,
    `/en/reviewer/reports/${id}?contact=1`,
    "/yo/reviewer/reports",
    "/en/projects",
    "/en/reviewer/sign-in",
    "javascript:alert(1)",
    "/en/reviewer/reports\n/x",
    "",
    `/en/reviewer/reports/${"a".repeat(300)}`
  ])("refuses %s", (value) => {
    expect(safeReviewerTarget("en", value)).toBeUndefined();
  });

  it("refuses anything that is not a single string", () => {
    expect(safeReviewerTarget("en", undefined)).toBeUndefined();
    expect(safeReviewerTarget("en", ["/en/reviewer/reports"])).toBeUndefined();
    expect(safeReviewerTarget("en", 7)).toBeUndefined();
  });
});

describe("signInPath and toSignInReason", () => {
  it("only carries an allowlisted reason and a safe non-default target", () => {
    expect(signInPath("en")).toBe("/en/reviewer/sign-in");
    expect(signInPath("en", { reason: "expired" })).toBe("/en/reviewer/sign-in?reason=expired");
    expect(signInPath("en", { next: queuePath("en") })).toBe("/en/reviewer/sign-in");
    expect(signInPath("en", { reason: "expired", next: `/en/reviewer/reports/${id}` })).toBe(
      `/en/reviewer/sign-in?reason=expired&next=${encodeURIComponent(`/en/reviewer/reports/${id}`)}`
    );
    expect(signInPath("en", { next: "https://evil.example" })).toBe("/en/reviewer/sign-in");
  });

  it("recognises only the two reasons", () => {
    expect(toSignInReason("expired")).toBe("expired");
    expect(toSignInReason("signed_out")).toBe("signed_out");
    expect(toSignInReason("<script>")).toBeUndefined();
    expect(toSignInReason(undefined)).toBeUndefined();
  });
});
