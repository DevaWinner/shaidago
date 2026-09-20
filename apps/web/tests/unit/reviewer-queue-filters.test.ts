import { describe, expect, it } from "vitest";

import { hasFilters, parseQueueFilters, queueHref, queueQuery } from "@/lib/reviewer/queue-filters";

describe("parseQueueFilters", () => {
  it("keeps only values from the API's own enumerations and pattern", () => {
    expect(
      parseQueueFilters({
        status: "under_review",
        risk: "high",
        category: "access_barrier",
        project: "synthetic-example-clinic",
        cursor: "abc123"
      })
    ).toEqual({
      status: "under_review",
      risk: "high",
      category: "access_barrier",
      project: "synthetic-example-clinic",
      cursor: "abc123"
    });
  });

  it.each([
    { status: "closed; drop table" },
    { risk: "critical" },
    { category: "" },
    { project: "Has Capitals" },
    { project: "a/b" },
    { project: "x".repeat(121) },
    { cursor: "has space" },
    { cursor: "x".repeat(513) },
    { status: ["received", "closed"] },
    { unknown: "value" }
  ])("drops %j", (search) => {
    expect(parseQueueFilters(search)).toEqual({});
  });
});

describe("queueQuery and queueHref", () => {
  it("builds the API query with a bounded page size and no unknown parameter", () => {
    expect(queueQuery({})).toEqual({ limit: 20 });
    expect(queueQuery({ status: "received", risk: "elevated", project: "p", cursor: "c" })).toEqual(
      {
        limit: 20,
        status: ["received"],
        risk_level: "elevated",
        project: "p",
        cursor: "c"
      }
    );
  });

  it("writes filters in a stable order and adds a cursor only when asked", () => {
    const filters = { risk: "high", status: "received" } as const;

    expect(queueHref("/en/reviewer/reports", {})).toBe("/en/reviewer/reports");
    expect(queueHref("/en/reviewer/reports", filters)).toBe(
      "/en/reviewer/reports?status=received&risk=high"
    );
    expect(
      queueHref("/en/reviewer/reports", { ...filters, cursor: "old" }, { cursor: "next" })
    ).toBe("/en/reviewer/reports?status=received&risk=high&cursor=next");
  });

  it("knows when a filter is set", () => {
    expect(hasFilters({})).toBe(false);
    expect(hasFilters({ cursor: "c" })).toBe(false);
    expect(hasFilters({ project: "p" })).toBe(true);
  });
});
