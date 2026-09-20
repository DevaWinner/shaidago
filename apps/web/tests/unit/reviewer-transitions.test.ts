import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import {
  CONSEQUENTIAL,
  NEEDS_MESSAGE,
  NEEDS_REASON,
  REVIEWER_TRANSITIONS,
  isReportStatus,
  transitionsFrom
} from "@/lib/reviewer/transitions";

type Machine = {
  state_machines: Record<
    string,
    { transitions?: { from: string; command: string; actors: string[]; to: string }[] }
  >;
};

const contract = JSON.parse(
  readFileSync(
    join(import.meta.dirname, "..", "..", "..", "..", "contracts", "controlled-vocabulary.json"),
    "utf8"
  )
) as Machine;

describe("REVIEWER_TRANSITIONS", () => {
  const rows = contract.state_machines["report_status"]?.transitions ?? [];
  const reviewerRows = rows.filter((row) => row.actors.includes("reviewer"));

  it("matches the report_status machine for reviewers exactly", () => {
    const fromContract = reviewerRows.map((row) => `${row.from}|${row.command}|${row.to}`).sort();
    const local = Object.entries(REVIEWER_TRANSITIONS)
      .flatMap(([from, list]) => list.map((item) => `${from}|${item.command}|${item.to}`))
      .sort();

    expect(local).toEqual(fromContract);
    expect(rows.length).toBeGreaterThan(reviewerRows.length);
  });

  it("never offers the reporter-only follow-up command", () => {
    const commands = Object.values(REVIEWER_TRANSITIONS).flatMap((list) =>
      list.map((item) => item.command)
    );

    expect(commands).not.toContain("record_follow_up");
  });

  it("knows which commands need a reason, a message, or a stronger warning", () => {
    expect([...NEEDS_REASON]).toEqual(["reopen"]);
    expect([...NEEDS_MESSAGE]).toEqual(["request_information"]);
    expect(CONSEQUENTIAL.has("close")).toBe(true);
    expect(CONSEQUENTIAL.has("start_review")).toBe(false);
  });

  it("offers nothing for a status it does not know", () => {
    expect(transitionsFrom("published")).toEqual([]);
    expect(isReportStatus("closed")).toBe(true);
    expect(isReportStatus("published")).toBe(false);
    expect(transitionsFrom("closed")).toEqual([{ command: "reopen", to: "under_review" }]);
  });
});
