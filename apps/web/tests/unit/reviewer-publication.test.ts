import { describe, expect, it } from "vitest";

import { citationOptions, issueKind, parsePreview } from "@/lib/reviewer/publication";
import type { ProjectDetail } from "@/lib/api/public-data";

const uuid = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const citation = (n: number, label = "Page 1", passage = "An exact passage.") => ({
  canonical_url: "https://example.org/x",
  information_class: "official_source",
  location_label: label,
  passage,
  publisher: "Synthetic Publisher",
  retrieved_at: "2026-09-01T09:00:00Z",
  source_id: uuid(n),
  source_title: "Synthetic source",
  source_type: "government_publication",
  source_version_id: uuid(900 + n)
});
const preview = (over: Record<string, unknown> = {}) => ({
  public_update_id: uuid(1),
  state: "draft",
  project_slug: "synthetic-project-20",
  report_status: "verified_for_public_update",
  report_version: 4,
  update: {
    id: uuid(2),
    statement: "A neutral statement.",
    effective_on: "2026-09-01",
    last_checked_on: null,
    verification_state: "verified_official",
    information_class: "official_source",
    ai_generated: false,
    citations: [citation(1)]
  },
  issues: [],
  can_publish: true,
  preview_digest: "a".repeat(64),
  ...over
});

describe("parsePreview", () => {
  it("accepts a well-formed preview and keeps the public update exactly", () => {
    const parsed = parsePreview(preview());

    expect(parsed?.digest).toBe("a".repeat(64));
    expect(parsed?.update.statement).toBe("A neutral statement.");
    expect(parsed?.canPublish).toBe(true);
    expect(parsed?.reportVersion).toBe(4);
  });

  it.each([
    ["not an object", "x"],
    ["a short digest", preview({ preview_digest: "abc" })],
    ["a non-uuid id", preview({ public_update_id: "not-an-id" })],
    ["no issues array", preview({ issues: undefined })],
    ["a non-boolean can_publish", preview({ can_publish: "yes" })],
    ["an AI-generated update", preview({ update: { ...preview().update, ai_generated: true } })],
    [
      "an unknown verification state",
      preview({ update: { ...preview().update, verification_state: "true" } })
    ],
    [
      "six citations",
      preview({
        update: {
          ...preview().update,
          citations: Array.from({ length: 6 }, (_, i) => citation(i + 1))
        }
      })
    ],
    [
      "a malformed citation",
      preview({ update: { ...preview().update, citations: [{ passage: "x" }] } })
    ],
    ["a malformed issue", preview({ issues: [{ field: 1, code: "x" }] })]
  ])("refuses %s", (_name, value) => {
    expect(parsePreview(value)).toBeUndefined();
  });

  it("keeps issues so publishing can be blocked", () => {
    const parsed = parsePreview(
      preview({
        can_publish: false,
        issues: [{ field: "statement", code: "unsupported_term_corrupt" }]
      })
    );

    expect(parsed?.issues).toEqual([{ field: "statement", code: "unsupported_term_corrupt" }]);
    expect(parsed?.canPublish).toBe(false);
  });
});

describe("citationOptions", () => {
  const project = (facts: unknown[], updates: unknown[] = []) =>
    ({ facts, updates }) as unknown as ProjectDetail;

  it("offers each distinct approved citation of the project once, verbatim", () => {
    const options = citationOptions(
      project(
        [
          { citations: [citation(1), citation(2, "Page 2", "Another.")] },
          { citations: [citation(1)] }
        ],
        [{ citations: [citation(2, "Page 2", "Another.")] }]
      )
    );

    expect(options).toHaveLength(2);
    expect(options[0]).toMatchObject({
      sourceVersionId: uuid(901),
      passage: "An exact passage.",
      locationLabel: "Page 1"
    });
  });

  it("offers nothing when the record has no citations and caps a long list", () => {
    expect(citationOptions(project([{ citations: [] }]))).toEqual([]);
    const many = Array.from({ length: 60 }, (_, index) =>
      citation(index + 1, `P${index}`, `Passage ${index}`)
    );

    expect(citationOptions(project([{ citations: many }]))).toHaveLength(40);
  });
});

describe("issueKind", () => {
  it("separates an unsupported term from a known code and an odd one", () => {
    expect(issueKind("unsupported_term_corrupt")).toEqual({ kind: "term", term: "corrupt" });
    expect(issueKind("report_text")).toEqual({ kind: "known", key: "report_text" });
    expect(issueKind("Weird Code!")).toEqual({ kind: "other" });
    expect(issueKind("unsupported_term_<script>")).toEqual({ kind: "other" });
  });
});
