import { describe, expect, it } from "vitest";

import { cn } from "@/lib/utils";

describe("cn", () => {
  it("keeps a colour and a theme font size on the same element", () => {
    expect(cn("text-primary-foreground", "text-ledger-lg")).toBe(
      "text-primary-foreground text-ledger-lg"
    );
  });

  it("lets a later utility of the same kind win", () => {
    expect(cn("px-3", false, "px-6")).toBe("px-6");
    expect(cn("text-ledger-sm", "text-ledger-lg")).toBe("text-ledger-lg");
  });
});
