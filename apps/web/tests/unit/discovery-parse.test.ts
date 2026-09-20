import { describe, expect, it } from "vitest";

import {
  groupDuplicates,
  parseAnalysis,
  parseRun,
  parseSources,
  safeHttpUrl
} from "@/lib/discovery/parse";
import { analysisFor, defaultSources, manySources } from "../support/mock-discovery.mjs";

const reviewerRun = (over: Record<string, unknown> = {}) => {
  const sources = defaultSources("e1", true);

  return {
    run_id: "0198f1a2-7b3c-4d4e-8f5a-d00000000001",
    report_id: "0198f1a2-7b3c-4d4e-8f5a-000000000001",
    scope: "reviewer",
    status: "needs_review",
    version: 2,
    created_at: "2026-09-20T09:00:00Z",
    finished_at: "2026-09-20T09:01:00Z",
    demo_replay: true,
    failure_code: null,
    query_text: "Abuja AMAC public works official source",
    results_found: 3,
    fetched_count: 3,
    analysed_count: 3,
    cancel_requested: false,
    sources,
    analysis: analysisFor(sources),
    ...over
  };
};

describe("safeHttpUrl", () => {
  it("keeps plain http and https addresses only", () => {
    expect(safeHttpUrl("https://example.test/a")).toBe("https://example.test/a");
    expect(safeHttpUrl("http://example.test/")).toBe("http://example.test/");
    for (const bad of [
      "javascript:alert(1)",
      "data:text/html,x",
      "ftp://x.test",
      "https://u:p@x.test/",
      "not a url",
      5,
      "https://" + "a".repeat(2100)
    ]) {
      expect(safeHttpUrl(bad)).toBeUndefined();
    }
  });
});

describe("parseSources", () => {
  it("reads at most ten cards and drops an unsafe link without dropping the card", () => {
    const parsed = parseSources(defaultSources("e1", true));

    expect(parsed).toHaveLength(3);
    expect(parsed?.[2]?.url).toBeUndefined();
    expect(parsed?.[2]?.injectionFlag).toBe(true);
    expect(parsed?.[1]?.duplicateOf).toBe(parsed?.[0]?.id);
    expect(parseSources(manySources("e1", false, 10))).toHaveLength(10);
  });

  it("refuses more than ten, a bad identifier, or a malformed card", () => {
    expect(parseSources(manySources("e1", false, 11))).toBeUndefined();
    expect(
      parseSources([{ ...defaultSources("e1", false)[0], source_id: "nope" }])
    ).toBeUndefined();
    expect(parseSources([{ title: "x" }])).toBeUndefined();
    expect(parseSources("x")).toBeUndefined();
  });
});

describe("parseAnalysis", () => {
  const sources = parseSources(defaultSources("e1", true)) ?? [];

  it("resolves every citation to a source card of the same run and keeps categories apart", () => {
    const analysis = parseAnalysis(analysisFor(defaultSources("e1", true)), sources);

    expect(analysis?.facts[0]).toEqual({ text: expect.any(String), sources: [0] });
    expect(analysis?.claims[0]?.publisher).toBe("example.test");
    expect(analysis?.contradictions[0]?.sources).toEqual([0, 1]);
    expect(analysis?.gaps).toHaveLength(1);
    expect(analysis?.followUps).toHaveLength(2);
    expect(analysis?.safety).toContain("human review");
  });

  it("shows no analysis at all when a citation does not resolve", () => {
    expect(
      parseAnalysis(analysisFor(defaultSources("e1", true), { invalid: true }), sources)
    ).toBeUndefined();
  });

  it("refuses a contradiction with one side, a fact with no citation, six questions, and a duplicated citation id", () => {
    const base = analysisFor(defaultSources("e1", true));
    const with_ = (patch: Record<string, unknown>) => ({
      ...base,
      analysis: { ...base.analysis, ...patch }
    });

    expect(
      parseAnalysis(
        with_({ contradictions: [{ description: "x", citation_ids: ["s_fict1"] }] }),
        sources
      )
    ).toBeUndefined();
    expect(
      parseAnalysis(with_({ supported_facts: [{ text: "x", citation_ids: [] }] }), sources)
    ).toBeUndefined();
    expect(
      parseAnalysis(
        with_({
          follow_up_questions: Array.from({ length: 6 }, () => ({
            question: "q",
            reason: "r",
            sensitivity: "low"
          }))
        }),
        sources
      )
    ).toBeUndefined();
    expect(
      parseAnalysis({ ...base, sources: [...base.sources, base.sources[0]] }, sources)
    ).toBeUndefined();
    expect(parseAnalysis("x", sources)).toBeUndefined();
  });

  it("does not accept a source that is not in the run's own cards", () => {
    const foreign = {
      ...analysisFor(defaultSources("e1", true)),
      sources: [{ citation_id: "s_fict1", source_id: "0198f1a2-7b3c-4d4e-8f5a-ffffffffffff" }]
    };

    expect(parseAnalysis(foreign, sources)).toBeUndefined();
  });
});

describe("parseRun", () => {
  it("reads a reviewer run with its counts, query, and analysis", () => {
    const run = parseRun(reviewerRun(), "reviewer");

    expect(run?.scope).toBe("reviewer");
    expect(run?.counts).toEqual({ found: 3, fetched: 3, analysed: 3 });
    expect(run?.queryText).toContain("Abuja");
    expect(run?.analysis?.facts).toHaveLength(1);
  });

  it("reads a public run's analysis from result and never shows a query", () => {
    const value = reviewerRun();
    const publicRun = {
      run_id: value.run_id,
      status: "complete",
      version: 2,
      created_at: value.created_at,
      finished_at: value.finished_at,
      demo_replay: true,
      failure_code: null,
      progress: { results_found: 3, fetched: 3, analysed: 2 },
      sources: defaultSources("f1", false),
      result: analysisFor(defaultSources("f1", false))
    };
    const run = parseRun(publicRun, "public");

    expect(run?.queryText).toBeNull();
    expect(run?.analysis).toBeDefined();
    expect(parseRun({ ...publicRun, result: null }, "public")?.analysis).toBeUndefined();
  });

  it("refuses an unreadable run rather than rendering part of it", () => {
    expect(parseRun(reviewerRun({ version: -1 }), "reviewer")).toBeUndefined();
    expect(parseRun(reviewerRun({ run_id: "x" }), "reviewer")).toBeUndefined();
    expect(parseRun(reviewerRun({ failure_code: "Not A Code!!" }), "reviewer")).toBeUndefined();
    expect(parseRun(reviewerRun({ fetched_count: "3" }), "reviewer")).toBeUndefined();
    expect(parseRun(null, "public")).toBeUndefined();
  });
});

describe("groupDuplicates", () => {
  it("groups a repeat under the page it repeats, and leaves an orphan repeat as its own card", () => {
    const sources = parseSources(defaultSources("e1", true)) ?? [];
    const groups = groupDuplicates(sources);

    expect(groups).toHaveLength(2);
    expect(groups[0]?.duplicates).toHaveLength(1);
    const orphan = parseSources(defaultSources("e1", true).slice(1)) ?? [];

    expect(groupDuplicates(orphan)).toHaveLength(2);
  });
});
