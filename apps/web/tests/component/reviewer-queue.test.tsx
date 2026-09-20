import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { QueueFilterForm, QueueList } from "@/components/reviewer/queue";
import en from "../../messages/en.json";

afterEach(cleanup);

const item = (over: Record<string, unknown> = {}) => ({
  report_id: "0198f1a2-7b3c-4d4e-8f5a-000000000001",
  project_slug: "synthetic-example-clinic",
  concern_category: "incomplete_work",
  risk_level: "high",
  status: "under_review",
  version: 2,
  created_at: "2026-09-03T09:00:00Z",
  status_updated_at: "2026-09-04T10:00:00Z",
  has_contact: true,
  evidence_count: 2,
  open_follow_ups: 1,
  ...over
});

const list = (items: ReturnType<typeof item>[]) =>
  render(<QueueList copy={en.reviewer.queue} items={items} language="en" locale="en" />);

describe("QueueList", () => {
  it("states status and risk in words and shows only triage facts", () => {
    list([item()]);
    const row = document.querySelector<HTMLElement>("[data-slot=queue-item]") as HTMLElement;

    expect(within(row).getByText("Status: Under review")).toBeTruthy();
    expect(within(row).getByText("Risk: High")).toBeTruthy();
    expect(within(row).getByText("Incomplete work")).toBeTruthy();
    expect(within(row).getByText("2 files")).toBeTruthy();
    expect(within(row).getByText("1 open question")).toBeTruthy();
    expect(within(row).getByText("Contact details provided")).toBeTruthy();
    expect(within(row).getByText(/Received 3 September 2026/)).toBeTruthy();
  });

  it("links to the report by a plain anchor with a name that says which report", () => {
    list([item()]);
    const link = screen.getByRole("link", {
      name: "Open report for synthetic-example-clinic, received 3 September 2026"
    });

    expect(link.getAttribute("href")).toBe(
      "/en/reviewer/reports/0198f1a2-7b3c-4d4e-8f5a-000000000001"
    );
    expect(link.getAttribute("data-prefetch")).toBeNull();
  });

  it("says when there are no files, questions, or contact, and copes with a long name", () => {
    list([
      item({
        evidence_count: 0,
        open_follow_ups: 0,
        has_contact: false,
        project_slug: `synthetic-${"long-".repeat(20)}record`
      })
    ]);

    expect(screen.getByText("No files")).toBeTruthy();
    expect(screen.getByText("No open questions")).toBeTruthy();
    expect(screen.getByText("No contact details")).toBeTruthy();
  });

  it("renders a maximum page without dropping a row", () => {
    list(
      Array.from({ length: 50 }, (_, index) =>
        item({ report_id: `0198f1a2-7b3c-4d4e-8f5a-${String(index).padStart(12, "0")}` })
      )
    );

    expect(document.querySelectorAll("[data-slot=queue-item]")).toHaveLength(50);
  });

  it("never renders a description, a contact value, or a note", () => {
    list([item({ description: "SECRET-DESCRIPTION", contact: { value: "SECRET-CONTACT" } })]);

    expect(document.body.textContent).not.toContain("SECRET");
  });
});

describe("QueueFilterForm", () => {
  it("is a GET form with labelled controls that keep the chosen values and no cursor", () => {
    render(
      <QueueFilterForm
        action="/en/reviewer/reports"
        clearHref="/en/reviewer/reports"
        copy={en.reviewer.queue}
        filters={{ status: "received", cursor: "abc" }}
      />
    );

    const form = screen.getByRole("form", { name: "Filter the queue" });

    expect(form.getAttribute("method")).toBe("get");
    expect((screen.getByLabelText("Status") as HTMLSelectElement).value).toBe("received");
    expect(form.querySelector('[name="cursor"]')).toBeNull();
    expect(screen.getByRole("link", { name: "Clear filters" }).getAttribute("href")).toBe(
      "/en/reviewer/reports"
    );
  });
});
