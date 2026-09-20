import { describe, expect, it } from "vitest";

import { toSafeRequestReference } from "@/lib/support/request-reference";

describe("toSafeRequestReference", () => {
  it("normalises an accepted UUID request ID", () => {
    expect(toSafeRequestReference("A1000000-0000-7000-8000-000000000001")).toBe(
      "a1000000-0000-7000-8000-000000000001"
    );
  });

  it.each([
    undefined,
    null,
    42,
    "",
    "provider response: do not show this",
    "a1000000-0000-0000-0000-000000000001",
    "a1000000-0000-7000-7000-000000000001",
    "a1000000-0000-7000-8000-000000000001\nstack trace"
  ])("rejects unsafe support reference %#", (value) => {
    expect(toSafeRequestReference(value)).toBeUndefined();
  });
});
