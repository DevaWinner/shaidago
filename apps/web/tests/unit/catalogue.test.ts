import { describe, expect, it, vi } from "vitest";

import en from "../../messages/en.json";
import { formatMessage, resolveDomain } from "@/i18n/catalogue";
import { isDomainReviewed } from "@/i18n/routing";

describe("resolveDomain", () => {
  it("returns English as reviewed source copy, not flagged as an original", () => {
    const copy = resolveDomain("en", "shell");

    expect(copy.messages).toBe(en.shell);
    expect(copy).toMatchObject({ language: "en", isOriginal: false });
  });

  it("returns the flagged English original, never blank or partial text, for pending locales", () => {
    for (const locale of ["ha", "ig", "yo"] as const) {
      for (const domain of ["shell", "evidence", "landing", "recovery"] as const) {
        const copy = resolveDomain(locale, domain);

        expect(copy.language, `${locale}.${domain}`).toBe("en");
        expect(copy.isOriginal, `${locale}.${domain}`).toBe(true);
        expect(copy.messages, `${locale}.${domain}`).toBe(en[domain]);
      }
    }
  });

  it("marks every critical domain of a pending locale as an original so a notice is always shown", () => {
    expect(isDomainReviewed("ha", "shell")).toBe(false);
    expect(isDomainReviewed("en", "shell")).toBe(true);
    expect(resolveDomain("yo", "recovery").isOriginal).toBe(true);
  });

  it("falls back, flagged, when a domain is marked reviewed but has a pending key", async () => {
    vi.resetModules();
    vi.doMock("../../messages/status.json", async () => {
      const real = (
        await vi.importActual<{ default: Record<string, unknown> }>("../../messages/status.json")
      ).default as { domains: unknown; locales: Record<string, Record<string, unknown>> };

      return {
        default: {
          ...real,
          locales: {
            ...real.locales,
            ha: Object.fromEntries(
              Object.keys(real.locales["ha"] ?? {}).map((domain) => [
                domain,
                { status: "reviewed", reviewer: "test", reviewedOn: "2026-09-20" }
              ])
            )
          }
        }
      };
    });

    const { resolveDomain: resolveWithStatus } = await import("@/i18n/catalogue");
    const copy = resolveWithStatus("ha", "shell");

    // `ha.json` still holds nulls, so "reviewed" alone must not serve blanks.
    expect(copy).toMatchObject({ language: "en", isOriginal: true });
    vi.doUnmock("../../messages/status.json");
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
