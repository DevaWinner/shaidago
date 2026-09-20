import { describe, expect, it } from "vitest";

import {
  CATEGORIES,
  PAGE_SIZE,
  activeFilterNames,
  apiQuery,
  directoryHref,
  normaliseQuery,
  parseFilters,
  toQueryString,
  withoutFilter
} from "@/lib/directory/filters";

const localities = ["amac", "bwari", "abuja"];

describe("parseFilters", () => {
  it("accepts allowlisted values and reports no redirect for an already canonical URL", () => {
    const { filters, needsCanonicalRedirect } = parseFilters(
      {
        q: "clinic",
        locality: "amac",
        category: "health",
        status: "planned",
        verification: "corroborated",
        cursor: "abc_DEF-1.2~="
      },
      localities
    );

    expect(filters).toEqual({
      q: "clinic",
      locality: "amac",
      category: "health",
      status: "planned",
      verification: "corroborated",
      cursor: "abc_DEF-1.2~="
    });
    expect(needsCanonicalRedirect).toBe(false);
  });

  it("drops unknown values, unknown names, and malformed cursors, and asks for a canonical redirect", () => {
    const cases: Record<string, unknown>[] = [
      { locality: "nowhere" },
      { locality: "AMAC" },
      { category: "weapons" },
      { status: "corrupt" },
      { verification: "true" },
      { cursor: "has space" },
      { cursor: "x".repeat(513) },
      { cursor: "a%b" },
      { utm_source: "x" },
      { q: "   " }
    ];

    for (const params of cases) {
      const { filters, needsCanonicalRedirect } = parseFilters(params as never, localities);

      expect(filters, JSON.stringify(params)).toEqual({});
      expect(needsCanonicalRedirect, JSON.stringify(params)).toBe(true);
    }
  });

  it("keeps the first of a repeated parameter and redirects to the canonical form", () => {
    const { filters, needsCanonicalRedirect } = parseFilters(
      { category: ["health", "education"] },
      localities
    );

    expect(filters).toEqual({ category: "health" });
    expect(needsCanonicalRedirect).toBe(true);
  });

  it("normalises the search text and redirects only when it changed", () => {
    expect(normaliseQuery("  road   repair  ")).toBe("road repair");
    expect(normaliseQuery("x".repeat(150))?.length).toBe(100);
    expect(normaliseQuery("")).toBeUndefined();
    expect(parseFilters({ q: "  road   repair " }, localities)).toEqual({
      filters: { q: "road repair" },
      needsCanonicalRedirect: true
    });
  });

  it("treats an empty URL as canonical", () => {
    expect(parseFilters({}, localities)).toEqual({ filters: {}, needsCanonicalRedirect: false });
  });

  it("never lets a hostile value through to a backend filter", () => {
    const hostile = [
      "'; DROP TABLE projects;--",
      "<script>",
      "../../etc/passwd",
      "amac&admin=1",
      "%00"
    ];

    for (const value of hostile) {
      const { filters } = parseFilters(
        { locality: value, category: value, status: value, verification: value, cursor: value },
        localities
      );

      expect(filters, value).toEqual({});
    }
  });
});

describe("serialisation", () => {
  const filters = {
    q: "a&b c",
    locality: "bwari",
    category: CATEGORIES[1],
    cursor: "cur"
  } as const;

  it("writes a fixed order, encodes values, and omits the cursor unless asked", () => {
    expect(toQueryString(filters, { cursor: false })).toBe(
      "q=a%26b+c&locality=bwari&category=education"
    );
    expect(toQueryString(filters, { cursor: true })).toBe(
      "q=a%26b+c&locality=bwari&category=education&cursor=cur"
    );
    expect(toQueryString({}, { cursor: true })).toBe("");
  });

  it("round-trips through the parser to the same filters", () => {
    const parsed = parseFilters(
      Object.fromEntries(new URLSearchParams(toQueryString(filters, { cursor: true }))),
      localities
    );

    expect(parsed.filters).toEqual(filters);
    expect(parsed.needsCanonicalRedirect).toBe(false);
  });

  it("builds locale-prefixed hrefs with an optional results anchor and never a cursor by default", () => {
    expect(directoryHref("ha", filters)).toBe(
      "/ha/projects?q=a%26b+c&locality=bwari&category=education"
    );
    expect(directoryHref("yo", {}, { withResults: true })).toBe("/yo/projects#results");
    expect(directoryHref("en", filters, { cursor: true })).toContain("cursor=cur");
  });

  it("removes one filter and always drops the cursor, which depends on the whole set", () => {
    expect(withoutFilter(filters, "locality")).toEqual({ q: "a&b c", category: "education" });
    expect(withoutFilter({ cursor: "c" }, "q")).toEqual({});
    expect(activeFilterNames(filters)).toEqual(["q", "locality", "category"]);
  });

  it("builds a bounded API query from allowlisted values only", () => {
    expect(apiQuery({ locality: "amac", cursor: "c" })).toEqual({
      limit: PAGE_SIZE,
      locality: "amac",
      cursor: "c"
    });
    expect(apiQuery({})).toEqual({ limit: PAGE_SIZE });
    expect(apiQuery({ q: "x" }, 5).limit).toBe(5);
  });
});
