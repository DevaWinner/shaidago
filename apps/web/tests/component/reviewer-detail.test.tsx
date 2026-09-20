import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import {
  ContactSection,
  EvidenceSection,
  HandleSection,
  HistorySection,
  ObservationSection,
  QuestionsList,
  detailContext
} from "@/components/reviewer/report-detail";
import type { components } from "@/lib/api/generated/schema";
import en from "../../messages/en.json";

afterEach(cleanup);

type Report = components["schemas"]["ReportDetailOut"];

const context = detailContext(en.reviewer.detail, en.reviewer.queue, "en", "en");
const base: Report = {
  report_id: "0198f1a2-7b3c-4d4e-8f5a-000000000001",
  project_slug: "synthetic-example-clinic",
  concern_category: "unsafe_construction",
  risk_level: "elevated",
  status: "under_review",
  version: 3,
  created_at: "2026-09-03T09:00:00Z",
  status_updated_at: "2026-09-04T10:00:00Z",
  has_contact: true,
  description: "Line one\n<script>window.__pwned = 1</script> <b>bold</b>",
  events: [],
  follow_ups: [],
  evidence: [],
  track_record: null,
  contact: null
};

describe("ObservationSection", () => {
  it("shows the description as plain text and never as markup", () => {
    const { container } = render(<ObservationSection context={context} report={base} />);

    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(screen.getByText(/<script>window.__pwned = 1<\/script>/)).toBeTruthy();
    expect(screen.getByText("Unsafe construction")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open the public record" }).getAttribute("href")).toBe(
      "/en/projects/synthetic-example-clinic"
    );
  });
});

describe("EvidenceSection", () => {
  const file = (over: Record<string, unknown> = {}) => ({
    evidence_id: "0198f1a2-7b3c-4d4e-8f5a-a00000000001",
    display_name: "evidence-1.jpg",
    mime_type: "image/jpeg",
    size_bytes: 2048,
    sanitation_state: "sanitised",
    scan_state: "clean",
    created_at: "2026-09-01T09:05:00Z",
    ...over
  });

  it("names cleaning and scan state, and warns when the demo did not scan", () => {
    render(
      <EvidenceSection
        context={context}
        renderDownload={() => null}
        report={{
          ...base,
          evidence: [
            file(),
            file({ evidence_id: "b", scan_state: "not_scanned_demo", size_bytes: 12 })
          ]
        }}
      />
    );

    expect(screen.getByText("No malware found")).toBeTruthy();
    expect(screen.getByText("2 KB")).toBeTruthy();
    expect(screen.getByText("12 bytes")).toBeTruthy();
    expect(screen.getByText(/has no malware scanner/)).toBeTruthy();
    expect(document.querySelector("img, iframe, embed, object, video, audio")).toBeNull();
  });

  it("says when nothing was attached and puts the download control where the caller says", () => {
    const { rerender } = render(
      <EvidenceSection context={context} renderDownload={() => null} report={base} />
    );

    expect(screen.getByText("No files were attached.")).toBeTruthy();
    rerender(
      <EvidenceSection
        context={context}
        renderDownload={(item) => <button type="button">get {item.display_name}</button>}
        report={{ ...base, evidence: [file()] }}
      />
    );
    expect(screen.getByRole("button", { name: "get evidence-1.jpg" })).toBeTruthy();
  });
});

describe("ContactSection", () => {
  const mount = (outcome: "not_requested" | "shown" | "denied" | "unavailable", report = base) =>
    render(
      <ContactSection
        context={context}
        hideHref="/en/reviewer/reports/x"
        outcome={outcome}
        report={report}
        revealHref="/en/reviewer/reports/x"
      />
    );

  it("keeps contact hidden behind a reveal that is a GET form with no value in it", () => {
    const { container } = mount("not_requested", {
      ...base,
      contact: { channel: "email", value: "SECRET" }
    });

    expect(container.textContent).not.toContain("SECRET");
    expect(screen.getByRole("button", { name: "Show contact details" })).toBeTruthy();
    expect(container.querySelector("form")?.getAttribute("method")).toBe("get");
    expect(screen.getByText("Showing them is recorded in the audit log.")).toBeTruthy();
  });

  it("shows the contact only after the reveal and offers hiding it again", () => {
    mount("shown", { ...base, contact: { channel: "email", value: "person@example.invalid" } });

    expect(screen.getByText("email: person@example.invalid")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Hide contact details" })).toBeTruthy();
  });

  it("says why it is not shown when the account is not allowed or the service failed", () => {
    mount("denied");
    expect(screen.getByText("This account is not allowed to see contact details.")).toBeTruthy();
    cleanup();
    mount("unavailable");
    expect(screen.getByText("The contact details could not be shown right now.")).toBeTruthy();
  });

  it("says so when there is no contact at all", () => {
    mount("not_requested", { ...base, has_contact: false });
    expect(screen.getByText("The reporter gave no contact details.")).toBeTruthy();
  });
});

describe("HistorySection, QuestionsList, HandleSection", () => {
  it("lists newest first, separating what the reporter saw from the internal reason", () => {
    render(
      <HistorySection
        context={context}
        report={{
          ...base,
          events: [
            {
              event_id: "1",
              previous_status: null,
              new_status: "received",
              public_message: "Received.",
              actor_type: "system",
              occurred_at: "2026-09-01T09:00:00Z",
              internal_reason: null
            },
            {
              event_id: "2",
              previous_status: "received",
              new_status: "under_review",
              public_message: "",
              actor_type: "reviewer",
              occurred_at: "2026-09-02T09:00:00Z",
              internal_reason: "Private reason"
            }
          ]
        }}
      />
    );
    const items = within(screen.getByRole("list")).getAllByRole("listitem");

    expect(items[0]?.textContent).toContain("From Received to Under review");
    expect(items[0]?.textContent).toContain("No message shown to the reporter.");
    expect(items[0]?.textContent).toContain("Internal reason (private): Private reason");
    expect(items[1]?.textContent).toContain("Set to Received");
    expect(items[1]?.textContent).not.toContain("Internal reason");
  });

  it("shows answered, unanswered, and withdrawn questions", () => {
    render(
      <QuestionsList
        context={context}
        report={{
          ...base,
          follow_ups: [
            {
              question_id: "1",
              question: "Q1",
              asked_at: "2026-09-01T09:00:00Z",
              withdrawn: false,
              answer_kind: "answered",
              answer: "A1"
            },
            {
              question_id: "2",
              question: "Q2",
              asked_at: "2026-09-01T09:00:00Z",
              withdrawn: false,
              answer_kind: null,
              answer: null
            },
            {
              question_id: "3",
              question: "Q3",
              asked_at: "2026-09-01T09:00:00Z",
              withdrawn: true,
              answer_kind: null,
              answer: null
            }
          ]
        }}
      />
    );

    expect(screen.getByText(/Answer \(answered\):/)).toBeTruthy();
    expect(screen.getByText("Not answered yet.")).toBeTruthy();
    expect(screen.getByText("Withdrawn")).toBeTruthy();
  });

  it("presents a handle as context, not proof", () => {
    render(
      <HandleSection
        context={context}
        report={{
          ...base,
          track_record: {
            handle: "h-1",
            reports_total: 4,
            verified_for_public_update: 2,
            closed: 1
          }
        }}
      />
    );

    expect(screen.getByText(/pseudonym, not proof/)).toBeTruthy();
    expect(screen.getByText("h-1")).toBeTruthy();
  });
});
