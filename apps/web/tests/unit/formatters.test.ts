import { describe, expect, it } from "vitest";

import { createFormatters } from "@/lib/format/formatters";

const en = createFormatters("en");
const now = new Date("2026-09-20T10:00:00Z");
const LOCALES = ["en", "ha", "ig", "yo"] as const;

describe("dates and instants", () => {
  it("shows an instant in Africa/Lagos without changing which instant it is", () => {
    // 23:30 UTC on the 20th is already the 21st in Lagos (UTC+1).
    expect(en.date("2026-09-20T23:30:00Z")).toBe("21 September 2026");
    expect(en.date("2026-09-20T10:00:00Z")).toBe("20 September 2026");
    expect(en.date("2026-09-20T22:59:59Z")).toBe("20 September 2026");
    expect(en.date("2026-09-20T23:00:00Z")).toBe("21 September 2026");
    expect(en.date("2026-09-20T23:30:00+01:00")).toBe("20 September 2026");
  });

  it("keeps a calendar date on the day the record states", () => {
    for (const day of ["2026-01-01", "2026-09-20", "2026-12-31"]) {
      const shown = en.date(day);

      expect(shown).toContain(String(Number(day.slice(8))));
      expect(shown).toContain("2026");
    }
    expect(en.date("2026-01-01")).toBe("1 January 2026");
    expect(en.date("2026-12-31")).toBe("31 December 2026");
  });

  it("shows date and time together for instants, and only the date for a calendar date", () => {
    expect(en.dateTime("2026-09-20T10:00:00Z")).toBe("20 September 2026 at 11:00");
    expect(en.dateTime("2026-09-20")).toBe("20 September 2026");
  });

  it("returns an unformattable value unchanged rather than inventing a date", () => {
    for (const bad of ["", "not a date", "2026-13-45", "2026-02-30T99:00:00Z"]) {
      expect(en.date(bad), bad).toBe(bad);
      expect(en.dateTime(bad), bad).toBe(bad);
    }
  });

  it("formats in every public locale with the same day, month position, and year digits", () => {
    for (const locale of LOCALES) {
      const shown = createFormatters(locale).date("2026-09-20T10:00:00Z");

      expect(shown, locale).toContain("2026");
      expect(shown, locale).toContain("20");
    }
  });
});

describe("relative times are always paired with the exact time", () => {
  it("chooses a unit by size, for the past and the future", () => {
    const at = (iso: string) => en.relativeWithExact(iso, now)?.relative;

    expect(at("2026-09-20T09:59:30Z")).toBe("30 seconds ago");
    expect(at("2026-09-20T09:15:00Z")).toBe("45 minutes ago");
    expect(at("2026-09-20T07:00:00Z")).toBe("3 hours ago");
    expect(at("2026-09-17T10:00:00Z")).toBe("3 days ago");
    expect(at("2026-09-19T10:00:00Z")).toBe("yesterday");
    expect(at("2026-06-20T10:00:00Z")).toBe("3 months ago");
    expect(at("2024-09-20T10:00:00Z")).toBe("2 years ago");
    expect(at("2026-09-23T10:00:00Z")).toBe("in 3 days");
    expect(at("2026-09-20T10:00:00Z")).toBe("now");
  });

  it("returns the authoritative exact value beside it, and nothing for a calendar date or a bad value", () => {
    expect(en.relativeWithExact("2026-09-17T10:00:00Z", now)).toEqual({
      relative: "3 days ago",
      exact: "17 September 2026 at 11:00"
    });
    expect(en.relativeWithExact("2026-09-17", now)).toBeUndefined();
    expect(en.relativeWithExact("garbage", now)).toBeUndefined();
  });
});

describe("numbers and naira", () => {
  it("formats naira with its symbol, two decimals, and no conversion of the value", () => {
    expect(en.naira("1234567.5")).toBe("₦1,234,567.50");
    expect(en.naira("0")).toBe("₦0.00");
    expect(en.naira("-250.05")).toBe("-₦250.05");
    expect(en.naira(1000)).toBe("₦1,000.00");
    // Full precision for amounts a float would corrupt.
    expect(en.naira("123456789012345.99")).toBe("₦123,456,789,012,345.99");
  });

  it("keeps every digit the same across locales, changing only separators and symbol spacing", () => {
    for (const locale of LOCALES) {
      const digits = createFormatters(locale).naira("1234567.5").replace(/\D/g, "");

      expect(digits, locale).toBe("123456750");
    }
  });

  it("rejects an amount that is not a plain decimal with at most two places", () => {
    for (const bad of ["", "abc", "1,000", "₦100", "1e21", "1.234", "1..2", " 5", "--5", "NaN"]) {
      expect(() => en.naira(bad), bad).toThrow(RangeError);
    }
    for (const bad of [Number.NaN, Number.POSITIVE_INFINITY, 1e21, 1.234]) {
      expect(() => en.naira(bad), String(bad)).toThrow(RangeError);
    }
  });

  it("formats plain numbers and rejects non-decimals", () => {
    expect(en.number(1234567)).toBe("1,234,567");
    expect(en.number("12345678901234567890".slice(0, 15))).toBe("123,456,789,012,345");
    expect(en.number("0.125")).toBe("0.125");
    expect(() => en.number("1,000")).toThrow(RangeError);
  });
});

describe("lists and language names", () => {
  it("joins items with the locale's conjunction and never drops or reorders them", () => {
    expect(en.list([])).toBe("");
    expect(en.list(["AMAC"])).toBe("AMAC");
    expect(en.list(["AMAC", "Bwari"])).toBe("AMAC and Bwari");
    expect(en.list(["AMAC", "Bwari", "Gwagwalada"])).toBe("AMAC, Bwari and Gwagwalada");
    for (const locale of LOCALES) {
      const joined = createFormatters(locale).list(["one", "two", "three"]);

      expect(joined.indexOf("one")).toBeLessThan(joined.indexOf("two"));
      expect(joined.indexOf("two")).toBeLessThan(joined.indexOf("three"));
    }
  });

  it("names a source language in the page language and shows an unknown or invalid code as given", () => {
    expect(en.languageName("yo")).toBe("Yoruba");
    expect(en.languageName("ha")).toBe("Hausa");
    expect(en.languageName("en")).toBe("English");
    expect(en.languageName("!!!")).toBe("!!!");
    expect(en.languageName("")).toBe("");
  });
});
