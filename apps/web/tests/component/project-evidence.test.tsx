import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProjectDetailView } from "@/components/project/project-detail";
import { SourceView } from "@/components/project/source-view";
import { TrustContent } from "@/components/project/trust-content";
import type { Citation, Fact, ProjectDetail, SourceExcerpts } from "@/lib/api/public-data";
import { createFormatters } from "@/lib/format/formatters";
import en from "../../messages/en.json";

const now = new Date("2026-09-20T12:00:00Z");
const format = createFormatters("en");
const citation = (over: Partial<Citation> = {}): Citation => ({
  canonical_url: "https://example.org/synthetic",
  information_class: "official_source",
  location_label: "Page 2",
  passage: "A synthetic passage.",
  publisher: "Synthetic Ministry",
  retrieved_at: "2026-09-01T09:00:00Z",
  source_id: "00000000-0000-4000-8000-000000000001",
  source_version_id: "00000000-0000-4000-8000-0000000000a1",
  source_title: "Synthetic bulletin",
  source_type: "government_publication",
  ...over
});
const fact = (id: string, over: Partial<Fact> = {}): Fact => ({
  ai_generated: false,
  citations: [citation()],
  effective_on: null,
  id,
  information_class: "official_source",
  kind: "opaque_kind",
  last_checked_on: "2026-09-10",
  statement: `Statement ${id}`,
  verification_state: "awaiting_verification",
  ...over
});
const project = (over: Partial<ProjectDetail> = {}): ProjectDetail => ({
  category: "health",
  facts: [],
  last_checked_on: "2026-09-10",
  locality_slug: "amac",
  public_status: "planned",
  slug: "synthetic-project-01",
  text: {
    is_fallback: false,
    promised_deliverable: "",
    requested_locale: "en",
    reviewed_at: null,
    served_locale: "en",
    summary: "A fictional record.",
    title: "Synthetic record",
    translation_status: "reviewed"
  },
  updated_at: "2026-09-10T09:00:00Z",
  updates: [],
  ...over
});
const render_ = (detail: ProjectDetail) =>
  render(
    <ProjectDetailView
      copy={{
        directory: en.directory,
        evidence: en.evidence,
        project: en.project,
        source: en.source
      }}
      format={format}
      language="en"
      locale="en"
      localityName="Synthetic Area Council A"
      now={now}
      project={detail}
    />
  );

describe("ProjectDetailView", () => {
  it("shows only cited statements and states what is missing", () => {
    render_(
      project({
        facts: [fact("a"), fact("b", { citations: [] })],
        last_checked_on: "2026-01-01"
      })
    );

    expect(screen.getByText("Statement a")).toBeTruthy();
    expect(screen.queryByText("Statement b")).toBeNull();
    expect(screen.getByText(en.project.promised.notRecorded)).toBeTruthy();
    expect(screen.getByText(/last checked more than/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: en.project.unknown.heading })).toBeTruthy();
  });

  it("links the report action with the project slug and each citation to its source page", () => {
    render_(project({ facts: [fact("a")] }));

    expect(
      screen
        .getAllByRole("link")
        .some((link) =>
          link.getAttribute("href")?.endsWith("/en/report?project=synthetic-project-01")
        )
    ).toBe(true);
    const evidence = screen.getByRole("complementary");
    expect(
      within(evidence)
        .getByRole("link", { name: /source page/i })
        .getAttribute("href")
    ).toBe("/en/projects/synthetic-project-01/sources/00000000-0000-4000-8000-000000000001");
  });

  it("labels a future-dated update as scheduled and an empty record as empty", () => {
    const { unmount } = render_(
      project({
        updates: [
          {
            ai_generated: false,
            citations: [citation()],
            effective_on: "2026-12-01",
            id: "u1",
            information_class: "official_source",
            last_checked_on: "2026-09-10",
            statement: "Completion scheduled.",
            verification_state: "verified_official"
          }
        ]
      })
    );

    expect(screen.getByText(en.project.timeline.scheduled)).toBeTruthy();
    unmount();
    render_(project());
    expect(screen.getByText(en.project.facts.empty)).toBeTruthy();
  });
});

const source = (
  over: Partial<SourceExcerpts["source"]> = {},
  passage = "Short."
): SourceExcerpts => ({
  excerpts: [{ cited_by: "fact", item_id: "f1", location_label: "Page 2", passage }],
  source: {
    availability: "temporarily_unavailable",
    availability_checked_at: "2026-09-10T09:00:00Z",
    canonical_url: "https://example.org/synthetic",
    id: "00000000-0000-4000-8000-000000000001",
    information_class: "official_source",
    publisher: "Synthetic Ministry",
    source_type: "government_publication",
    title: "Synthetic bulletin",
    ...over
  }
});
const view = (data: SourceExcerpts) =>
  render(
    <SourceView
      base="/en/projects/x"
      copy={en.source}
      evidence={en.evidence}
      format={format}
      source={data}
    />
  );

describe("SourceView", () => {
  it("explains an unavailable original and opens it safely", () => {
    view(source());

    expect(screen.getByText(/could not be reached when last checked/)).toBeTruthy();
    const link = screen.getByRole("link", { name: /Open the original source/ });
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.getAttribute("referrerpolicy")).toBe("no-referrer");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(screen.getByRole("link", { name: en.source.excerpts.seeUse }).getAttribute("href")).toBe(
      "/en/projects/x#fact-f1"
    );
  });

  it("collapses a long passage behind a native disclosure, and states an unchecked source", () => {
    view(source({ availability: "unchecked", availability_checked_at: null }, "x".repeat(600)));

    expect(screen.getByText(en.source.excerpts.showFull).closest("details")).toBeTruthy();
    expect(screen.getAllByText(en.source.facts.unchecked).length).toBeGreaterThan(0);
  });

  it("says so when no passage is published", () => {
    view({ ...source(), excerpts: [] });

    expect(screen.getByText(en.source.excerpts.empty)).toBeTruthy();
  });
});

describe("TrustContent", () => {
  it("explains every label with the same words the record pages use and links one correction route", () => {
    render(
      <TrustContent
        copy={en.trust}
        directoryHref="/en/projects"
        evidence={en.evidence}
        locale="en"
      />
    );

    expect(screen.getByRole("heading", { level: 1, name: en.trust.title })).toBeTruthy();
    expect(screen.getByText(en.evidence.verification.disputed)).toBeTruthy();
    expect(screen.getByText(en.trust.reporting.limit)).toBeTruthy();
    expect(screen.getByRole("link", { name: en.trust.correct.report }).getAttribute("href")).toBe(
      "/en/report"
    );
    expect(document.getElementById("sources")).toBeTruthy();
  });
});
