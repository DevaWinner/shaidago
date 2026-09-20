import { describe, expect, it } from "vitest";

import { QUESTION_MAX, interpretAnswer } from "@/lib/qa/answer";

const source = (id: string, over: Record<string, unknown> = {}) => ({
  citation_id: id,
  passage: `Passage ${id}`,
  publisher: "Synthetic Ministry",
  retrieved_at: "2026-09-01T09:00:00Z",
  section_label: "Page 2",
  source_id: "00000000-0000-4000-8000-000000000001",
  title: `Source ${id}`,
  url: "https://example.org/synthetic",
  ...over
});
const answer = (over: Record<string, unknown> = {}) => ({
  answer: "One. Two.",
  confidence_note: " A note. ",
  generated_at: "2026-09-19T09:00:00Z",
  insufficient_evidence: false,
  requested_locale: "en",
  retrieval: { chunks_considered: 3, mode: "keyword" },
  served_locale: "en",
  sources: [source("a"), source("b"), source("unused")],
  statements: [
    { text: "One.", citation_ids: ["b"] },
    { text: "Two.", citation_ids: ["a", "b", "a"] }
  ],
  ...over
});

describe("interpretAnswer", () => {
  it("numbers sources by first use, keeps each statement's own citations, and drops unused sources", () => {
    const outcome = interpretAnswer(answer());

    expect(outcome.kind).toBe("supported");
    if (outcome.kind !== "supported") {
      return;
    }
    expect(outcome.view.sources.map((item) => [item.number, item.citationId])).toEqual([
      [1, "b"],
      [2, "a"]
    ]);
    expect(outcome.view.statements.map((item) => item.sources)).toEqual([[1], [2, 1]]);
    expect(outcome.view.confidenceNote).toBe("A note.");
    expect(outcome.view.mode).toBe("keyword");
  });

  it("shows insufficient evidence with no statements, even if the response carries some", () => {
    const outcome = interpretAnswer(answer({ insufficient_evidence: true, answer: " " }));

    expect(outcome).toEqual({
      kind: "insufficient",
      answer: "",
      confidenceNote: "A note.",
      servedLocale: "en"
    });
  });

  it.each([
    ["an unknown citation", { statements: [{ text: "X.", citation_ids: ["missing"] }] }],
    ["a statement with no citation", { statements: [{ text: "X.", citation_ids: [] }] }],
    ["a blank statement", { statements: [{ text: "  ", citation_ids: ["a"] }] }],
    ["no statements", { statements: [] }],
    ["duplicate source ids", { sources: [source("a"), source("a")] }]
  ])("fails closed on %s", (_name, over) => {
    expect(interpretAnswer(answer(over))).toEqual({ kind: "rejected" });
  });

  it.each([
    ["a non-object", "text"],
    ["a missing field", { ...answer(), statements: undefined }],
    ["a bad timestamp", answer({ generated_at: "yesterday" })],
    ["an unknown mode", answer({ retrieval: { chunks_considered: 1, mode: "magic" } })],
    [
      "a javascript: source link",
      answer({ sources: [source("a", { url: "javascript:alert(1)" })] })
    ],
    ["a link that is not a URL", answer({ sources: [source("a", { url: "not a url" })] })],
    ["a non-uuid source id", answer({ sources: [source("a", { source_id: "x" })] })]
  ])("treats %s as an invalid response", (_name, value) => {
    expect(interpretAnswer(value)).toEqual({ kind: "invalid" });
  });

  it("bounds the question at the same length the BFF enforces", () => {
    expect(QUESTION_MAX).toBe(300);
  });
});
