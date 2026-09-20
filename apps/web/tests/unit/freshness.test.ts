import { describe, expect, it } from "vitest";

import { STALE_AFTER_DAYS, daysSinceChecked, isStale } from "@/lib/directory/freshness";

const now = new Date("2026-09-20T12:00:00Z");

describe("freshness", () => {
  it("counts whole days from the checked date and never goes negative", () => {
    expect(daysSinceChecked("2026-09-20", now)).toBe(0);
    expect(daysSinceChecked("2026-09-19", now)).toBe(1);
    expect(daysSinceChecked("2026-09-21", now)).toBe(0);
    expect(daysSinceChecked(null, now)).toBeUndefined();
    expect(daysSinceChecked("not a date", now)).toBeUndefined();
  });

  it("labels a record stale only after the threshold, and never when the date is missing", () => {
    expect(STALE_AFTER_DAYS).toBe(90);
    expect(isStale("2026-06-22", now)).toBe(false);
    expect(isStale("2026-06-21", now)).toBe(true);
    expect(isStale("2026-06-20", now)).toBe(true);
    expect(isStale("2020-01-01", now)).toBe(true);
    expect(isStale(null, now)).toBe(false);
  });
});
