import { describe, expect, it } from "vitest";

import { LOW_DATA_HEAD_SCRIPT, lowDataCookie, readLowDataChoice } from "@/lib/low-data";

describe("low-data preference cookie", () => {
  it("reads an explicit choice, and treats anything else as not chosen", () => {
    expect(readLowDataChoice("sg_low_data=1")).toBe("on");
    expect(readLowDataChoice("a=b; sg_low_data=0; c=d")).toBe("off");
    expect(readLowDataChoice("")).toBe("unset");
    expect(readLowDataChoice("sg_low_data=2")).toBe("unset");
    expect(readLowDataChoice("xsg_low_data=1")).toBe("unset");
  });

  it("writes a one-year, site-wide, same-site cookie with no identifier, secure over https", () => {
    expect(lowDataCookie(true, false)).toBe(
      "sg_low_data=1; Path=/; Max-Age=31536000; SameSite=Lax"
    );
    expect(lowDataCookie(false, true)).toBe(
      "sg_low_data=0; Path=/; Max-Age=31536000; SameSite=Lax; Secure"
    );
  });

  it("applies the stored choice before paint with a script that only reads the cookie and sets one attribute", () => {
    expect(LOW_DATA_HEAD_SCRIPT).toContain("sg_low_data");
    expect(LOW_DATA_HEAD_SCRIPT).not.toMatch(/fetch|XMLHttp|sendBeacon|localStorage|eval|Function/);
    const attributes = new Map<string, string>();
    const documentStub = {
      cookie: "sg_low_data=1",
      documentElement: { dataset: attributes as unknown as Record<string, string> }
    };

    new Function("document", LOW_DATA_HEAD_SCRIPT)({
      cookie: documentStub.cookie,
      documentElement: { dataset: {} as Record<string, string> }
    });
    const dataset: Record<string, string> = {};

    new Function("document", LOW_DATA_HEAD_SCRIPT)({
      cookie: "sg_low_data=1",
      documentElement: { dataset }
    });
    expect(dataset["lowData"]).toBe("true");
    new Function("document", LOW_DATA_HEAD_SCRIPT)({ cookie: "", documentElement: { dataset } });
    expect(dataset["lowData"]).toBe("false");
  });
});
