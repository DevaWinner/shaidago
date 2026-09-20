import { describe, expect, it, vi } from "vitest";

import en from "../../messages/en.json";
import ha from "../../messages/ha.json";
import ig from "../../messages/ig.json";
import yo from "../../messages/yo.json";

type Json = Record<string, unknown>;
type StatusFile = {
  domains: Record<string, unknown>;
  locales: Record<string, Record<string, unknown>>;
};
import { formatMessage, resolveDomain } from "@/i18n/catalogue";
import { isDomainReviewed } from "@/i18n/routing";

describe("resolveDomain", () => {
  it("returns English as reviewed source copy, not flagged as an original", () => {
    const copy = resolveDomain("en", "shell");

    expect(copy.messages).toBe(en.shell);
    expect(copy).toMatchObject({ language: "en", isOriginal: false });
  });

  it("serves a reviewed locale's own complete copy in its own language", () => {
    const catalogues = { ha, ig, yo };

    for (const locale of ["ha", "ig", "yo"] as const) {
      for (const domain of ["shell", "evidence", "landing", "recovery"] as const) {
        const copy = resolveDomain(locale, domain);

        expect(copy, `${locale}.${domain}`).toMatchObject({ language: locale, isOriginal: false });
        expect(copy.messages, `${locale}.${domain}`).toBe(catalogues[locale][domain]);
      }
    }
    expect(isDomainReviewed("ha", "shell")).toBe(true);
  });

  async function withMocks(
    status: (real: StatusFile) => StatusFile,
    catalogue?: (real: Json) => Json
  ) {
    vi.resetModules();
    vi.doMock("../../messages/status.json", async () => {
      const real = (await vi.importActual<{ default: StatusFile }>("../../messages/status.json"))
        .default;

      return { default: status(structuredClone(real)) };
    });
    if (catalogue !== undefined) {
      vi.doMock("../../messages/ha.json", async () => {
        const real = (await vi.importActual<{ default: Json }>("../../messages/ha.json")).default;

        return { default: catalogue(structuredClone(real)) };
      });
    }

    return import("@/i18n/catalogue");
  }

  it("returns the flagged English original when a domain is not reviewed, never blank or partial text", async () => {
    const { resolveDomain: resolveWith } = await withMocks((real) => {
      real.locales["ha"] = Object.fromEntries(
        Object.keys(real.domains).map((domain) => [domain, { status: "pending" }])
      );

      return real;
    });

    for (const domain of ["shell", "evidence", "landing", "recovery"] as const) {
      const copy = resolveWith("ha", domain);

      expect(copy, domain).toMatchObject({ language: "en", isOriginal: true });
      // A reset module graph reloads the JSON, so compare by value, not identity.
      expect(copy.messages, domain).toEqual(en[domain]);
    }
    vi.doUnmock("../../messages/status.json");
    vi.resetModules();
  });

  it("falls back, flagged, when a domain is marked reviewed but has a pending key", async () => {
    const { resolveDomain: resolveWith } = await withMocks(
      (real) => real,
      (real) => {
        (real["shell"] as Json)["public"] = {
          ...((real["shell"] as Json)["public"] as Json),
          productName: null
        };

        return real;
      }
    );

    expect(resolveWith("ha", "shell")).toMatchObject({ language: "en", isOriginal: true });
    // A domain that is complete still serves its own language.
    expect(resolveWith("ha", "recovery")).toMatchObject({ language: "ha", isOriginal: false });
    vi.doUnmock("../../messages/status.json");
    vi.doUnmock("../../messages/ha.json");
    vi.resetModules();
  });
});

describe("formatMessage", () => {
  it("applies plural and number rules to the catalogue's ICU strings", () => {
    const { sourceCount, sourceLabel } = en.landing.sample;

    expect(formatMessage("en", sourceCount, { count: 1 })).toBe("1 source");
    expect(formatMessage("en", sourceCount, { count: 3 })).toBe("3 sources");
    expect(formatMessage("en", sourceCount, { count: 0 })).toBe("0 sources");
    expect(formatMessage("en", sourceLabel, { number: 1 })).toBe("Source 1");
    expect(formatMessage("en", sourceLabel, { number: 1234 })).toBe("Source 1,234");
  });

  it("interpolates without altering the value", () => {
    expect(
      formatMessage("en", en.recovery.error.reference, { reference: "0198f1a2-7b3c-4d4e" })
    ).toBe("Support reference: 0198f1a2-7b3c-4d4e");
  });
});
