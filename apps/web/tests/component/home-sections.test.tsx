import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EntryPoints, LatestRecord, TrustAndSteps } from "@/components/landing/home-sections";
import type { Locality, ProjectSummary } from "@/lib/api/public-data";
import { createFormatters } from "@/lib/format/formatters";
import en from "../../messages/en.json";

const project: ProjectSummary = {
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
  }
};
const localities: Locality[] = [
  {
    slug: "abuja",
    name: "Synthetic State",
    kind: "state",
    parent_slug: null,
    enabled_locales: ["en"]
  },
  {
    slug: "amac",
    name: "Synthetic Area Council A",
    kind: "area_council",
    parent_slug: "abuja",
    enabled_locales: ["en"]
  }
];
const latest = (state: "ok" | "unavailable", record: ProjectSummary | undefined) =>
  render(
    <LatestRecord
      copy={en.home.latest}
      directory={en.directory}
      format={createFormatters("en")}
      locale="en"
      locality={localities[1]}
      project={record}
      state={state}
    />
  );

describe("latest record", () => {
  it("shows the record's own facts and a real date, and links to its page", () => {
    latest("ok", project);

    expect(screen.getByRole("link", { name: "Synthetic project" })).toHaveAttribute(
      "href",
      "/en/projects/synthetic-project-01"
    );
    expect(screen.getByText("Synthetic Area Council A")).toBeVisible();
    expect(screen.getByText(en.directory.statuses.planned)).toBeVisible();
    expect(document.querySelector("time")).toHaveAttribute("datetime", "2026-09-10");
  });

  it("keeps the page honest when the service is down or there are no records", () => {
    const { unmount } = latest("unavailable", undefined);
    expect(screen.getByText(en.home.latest.unavailable)).toBeVisible();
    expect(screen.queryByRole("article")).toBeNull();
    unmount();

    latest("ok", undefined);
    expect(screen.getByText(en.home.latest.empty)).toBeVisible();
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("shows a missing check date as such", () => {
    latest("ok", { ...project, last_checked_on: null });

    expect(screen.getByText(en.home.latest.notChecked)).toBeVisible();
    expect(document.querySelector("time")).toBeNull();
  });
});

describe("entry points", () => {
  const render_ = (
    categories: Parameters<typeof EntryPoints>[0]["categories"],
    list = localities
  ) =>
    render(
      <EntryPoints
        categories={categories}
        copy={en.home}
        directory={en.directory}
        localities={list}
        locale="ha"
      />
    );

  it("offers only area councils that exist and only categories that have records, as filtered links", () => {
    render_(["health", "education"]);

    const places = screen.getByRole("region", { name: en.home.localities.heading });
    expect(within(places).getAllByRole("link")).toHaveLength(2);
    expect(within(places).getByRole("link", { name: "Synthetic Area Council A" })).toHaveAttribute(
      "href",
      "/ha/projects?locality=amac#results"
    );
    expect(within(places).queryByText("Synthetic State")).toBeNull();
    const categories = screen.getByRole("region", { name: en.home.categories.heading });
    expect(
      within(categories)
        .getAllByRole("link")
        .map((link) => link.getAttribute("href"))
    ).toEqual(["/ha/projects?category=health#results", "/ha/projects?category=education#results"]);
  });

  it("omits a section rather than inventing entries when the API gave none", () => {
    const { container } = render_([], []);

    expect(container).toBeEmptyDOMElement();
  });
});

describe("trust and steps", () => {
  it("states the trust promise and the three steps, with the not-an-emergency-service limit", () => {
    render(<TrustAndSteps copy={en.home} locale="yo" />);

    expect(screen.getAllByRole("listitem").length).toBeGreaterThanOrEqual(6);
    expect(screen.getByRole("link", { name: en.home.trust.link })).toHaveAttribute(
      "href",
      "/yo/trust"
    );
    expect(screen.getByText(/not an emergency service/i)).toBeVisible();
  });
});
