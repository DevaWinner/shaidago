import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DirectoryResults } from "@/components/directory/directory-results";
import { FilterPills } from "@/components/directory/filter-pills";
import type { Locality, ProjectSummary } from "@/lib/api/public-data";
import { createFormatters } from "@/lib/format/formatters";
import en from "../../messages/en.json";

const copy = en.directory;
const localities: Locality[] = [
  {
    slug: "amac",
    name: "Synthetic Area Council A",
    kind: "area_council",
    parent_slug: "abuja",
    enabled_locales: ["en"]
  }
];
const now = new Date("2026-09-20T12:00:00Z");
const project = (over: Partial<ProjectSummary> = {}): ProjectSummary => ({
  slug: "synthetic-project-01",
  category: "health",
  public_status: "planned",
  locality_slug: "amac",
  last_checked_on: "2026-09-10",
  updated_at: "2026-09-10T09:00:00Z",
  text: {
    is_fallback: false,
    served_locale: "en",
    summary: "A fictional record.",
    title: "Synthetic project",
    translation_status: "reviewed"
  },
  ...over
});

function results(read: Parameters<typeof DirectoryResults>[0]["read"], filters = {}) {
  return render(
    <DirectoryResults
      copy={copy}
      evidence={en.evidence}
      filters={filters}
      format={createFormatters("en")}
      language="en"
      localities={localities}
      locale="en"
      now={now}
      read={read}
    />
  );
}

describe("directory results states", () => {
  it("explains a registry with no records, and does not call it a filter problem", () => {
    results({ state: "ok", data: { items: [], nextCursor: null } });

    expect(screen.getByRole("heading", { name: copy.states.empty.title })).toBeVisible();
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent(copy.states.empty.title);
  });

  it("distinguishes no matches from empty and offers one way out", () => {
    results({ state: "ok", data: { items: [], nextCursor: null } }, { category: "health" });

    expect(screen.getByRole("heading", { name: copy.states.noMatches.title })).toBeVisible();
    expect(screen.getByRole("link", { name: copy.form.clear })).toHaveAttribute(
      "href",
      "/en/projects#results"
    );
  });

  it("recovers from an invalid cursor with a link to the same filters on the first page", () => {
    results({ state: "invalid_cursor" }, { category: "health", cursor: "old" });

    expect(screen.getByRole("link", { name: copy.states.invalidCursor.first })).toHaveAttribute(
      "href",
      "/en/projects?category=health#results"
    );
  });

  it("states an unavailable service with a retry that keeps the filters and cursor", () => {
    results({ state: "unavailable", requestId: undefined }, { q: "clinic", cursor: "c1" });

    expect(screen.getByRole("link", { name: copy.states.unavailable.retry })).toHaveAttribute(
      "href",
      "/en/projects?q=clinic&cursor=c1#results"
    );
  });

  it("renders a record with one named action, plain facts, a real date, and a stale note in words", () => {
    results({
      state: "ok",
      data: { items: [project({ last_checked_on: "2026-01-01" })], nextCursor: null }
    });

    const card = screen.getByRole("article");
    expect(within(card).getAllByRole("link")).toHaveLength(1);
    expect(within(card).getByRole("link", { name: "Synthetic project" })).toHaveAttribute(
      "href",
      "/en/projects/synthetic-project-01"
    );
    expect(within(card).getByText("Synthetic Area Council A")).toBeVisible();
    expect(within(card).getByText(copy.categories.health)).toBeVisible();
    expect(within(card).getByText(copy.statuses.planned)).toBeVisible();
    expect(card.querySelector("time")).toHaveAttribute("datetime", "2026-01-01");
    expect(within(card).getByText("Last checked more than 90 days ago.")).toBeVisible();
  });

  it("shows a missing check date as such and never invents a source count or verification", () => {
    results({
      state: "ok",
      data: { items: [project({ last_checked_on: null })], nextCursor: null }
    });

    const card = screen.getByRole("article");
    expect(within(card).getByText(copy.card.notChecked)).toBeVisible();
    expect(card.querySelector("time")).toBeNull();
    expect(card).not.toHaveTextContent(/source count|sources?\b.*\d|verified|verification/i);
  });

  it("declares the language of API text and labels an original-language fallback", () => {
    results({
      state: "ok",
      data: {
        items: [project({ text: { ...project().text, is_fallback: true, served_locale: "en" } })],
        nextCursor: "next"
      }
    });

    expect(screen.getByRole("heading", { name: "Synthetic project" })).toHaveAttribute(
      "lang",
      "en"
    );
    expect(screen.getByText(en.evidence.translation.unavailable)).toBeVisible();
  });

  it("offers next and first-page links only when they exist, without ever putting a cursor in the first-page link", () => {
    const { rerender } = results(
      { state: "ok", data: { items: [project()], nextCursor: "c2" } },
      { q: "a" }
    );
    const nav = screen.getByRole("navigation", { name: copy.pagination.label });

    expect(within(nav).getByRole("link", { name: copy.pagination.next })).toHaveAttribute(
      "href",
      "/en/projects?q=a&cursor=c2#results"
    );
    expect(within(nav).queryByRole("link", { name: copy.pagination.first })).toBeNull();

    rerender(
      <DirectoryResults
        copy={copy}
        evidence={en.evidence}
        filters={{ q: "a", cursor: "c2" }}
        format={createFormatters("en")}
        language="en"
        localities={localities}
        locale="en"
        now={now}
        read={{ state: "ok", data: { items: [project()], nextCursor: null } }}
      />
    );
    const last = screen.getByRole("navigation", { name: copy.pagination.label });

    expect(within(last).getByRole("link", { name: copy.pagination.first })).toHaveAttribute(
      "href",
      "/en/projects?q=a#results"
    );
    expect(within(last).queryByRole("link", { name: copy.pagination.next })).toBeNull();
  });

  it("announces only the count, not the list", () => {
    results({
      state: "ok",
      data: { items: [project(), project({ slug: "b" })], nextCursor: null }
    });

    expect(screen.getByRole("status")).toHaveTextContent("Showing 2 project records.");
    expect(screen.getByRole("status").textContent).not.toContain("Synthetic project");
  });
});

describe("filter pills", () => {
  const pills = (filters: Parameters<typeof FilterPills>[0]["filters"]) =>
    render(
      <FilterPills
        copy={copy}
        evidence={en.evidence}
        filters={filters}
        locale="en"
        localities={localities}
      />
    );

  it("renders nothing when no filter is active", () => {
    const { container } = pills({});

    expect(container).toBeEmptyDOMElement();
  });

  it("names each active filter, links removal to the other filters, and clears all in one link", () => {
    pills({
      q: "clinic",
      locality: "amac",
      category: "health",
      verification: "corroborated",
      cursor: "c"
    });
    const nav = screen.getByRole("navigation", { name: copy.pills.label });

    expect(
      within(nav).getByRole("link", { name: "Remove filter: Search: clinic" })
    ).toHaveAttribute(
      "href",
      "/en/projects?locality=amac&category=health&verification=corroborated#results"
    );
    expect(
      within(nav).getByRole("link", { name: "Remove filter: Synthetic Area Council A" })
    ).toBeVisible();
    expect(within(nav).getByRole("link", { name: "Remove filter: Health" })).toBeVisible();
    expect(
      within(nav).getByRole("link", {
        name: `Remove filter: ${en.evidence.verification.corroborated}`
      })
    ).toBeVisible();
    expect(within(nav).getAllByRole("link")).toHaveLength(5);
    expect(within(nav).getByRole("link", { name: copy.form.clear })).toHaveAttribute(
      "href",
      "/en/projects#results"
    );
    expect(nav.innerHTML).not.toContain("cursor");
  });
});
