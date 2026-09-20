import { describe, expect, it } from "vitest";

import { RECOVERY } from "@/lib/recovery-copy";
import en from "../../messages/en.json";

describe("recovery copy", () => {
  it("equals the English catalogue exactly, so the small client module cannot drift", () => {
    expect(RECOVERY).toEqual(en.recovery);
  });
});
