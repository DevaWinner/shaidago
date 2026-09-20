import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PublicUpdatePanel } from "@/components/reviewer/public-update-panel";
import type { CitationOption } from "@/lib/reviewer/publication";
import en from "../../messages/en.json";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000004";
const uuid = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
const OPTIONS: CitationOption[] = [
  {
    key: "a",
    sourceVersionId: uuid(901),
    passage: "The works are planned for the synthetic council.",
    locationLabel: "Page 2",
    publisher: "Synthetic Publisher",
    sourceTitle: "Synthetic bulletin"
  },
  {
    key: "b",
    sourceVersionId: uuid(902),
    passage: "Residents visited the synthetic site.",
    locationLabel: "Note 1",
    publisher: "Synthetic Community",
    sourceTitle: "Synthetic note"
  }
];
const entryCopy = {
  directory: en.directory,
  evidence: en.evidence,
  project: en.project,
  source: en.source
};
const preview = (over: Record<string, unknown> = {}) => ({
  public_update_id: uuid(1),
  state: "draft",
  project_slug: "synthetic-project-20",
  report_status: "verified_for_public_update",
  report_version: 4,
  update: {
    id: uuid(2),
    statement: "Works were recorded as planned.",
    effective_on: "2026-09-01",
    last_checked_on: null,
    verification_state: "verified_official",
    information_class: "official_source",
    ai_generated: false,
    citations: [
      {
        canonical_url: "https://example.org/x",
        information_class: "official_source",
        location_label: "Page 2",
        passage: "The works are planned for the synthetic council.",
        publisher: "Synthetic Publisher",
        retrieved_at: "2026-09-01T09:00:00Z",
        source_id: uuid(5),
        source_title: "Synthetic bulletin",
        source_type: "government_publication",
        source_version_id: uuid(901)
      }
    ]
  },
  issues: [],
  can_publish: true,
  preview_digest: "b".repeat(64),
  ...over
});
const problem = (code: string, status: number) =>
  new Response(JSON.stringify({ code, status }), {
    status,
    headers: { "Content-Type": "application/problem+json" }
  });
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

type Props = Partial<Parameters<typeof PublicUpdatePanel>[0]>;

const mount = (over: Props = {}) =>
  render(
    <PublicUpdatePanel
      actions={en.reviewer.actions}
      copy={en.reviewer.publication}
      drafts={[]}
      entryCopy={entryCopy}
      language="en"
      locale="en"
      now="2026-09-20T09:00:00Z"
      options={OPTIONS}
      problems={en.problems}
      projectHref="/en/projects/synthetic-project-20"
      reportId={REPORT}
      reportVerified
      signInHref="/en/reviewer/sign-in?reason=expired"
      {...over}
    />
  );

async function fillAndPreview(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/^Public statement/), "Works were recorded as planned.");
  await user.type(screen.getByLabelText(/^Date this applies from/), "2026-09-01");
  await user.click(screen.getByRole("checkbox", { name: /Synthetic bulletin/ }));
  await user.click(screen.getByRole("button", { name: "Create a preview" }));
}

beforeEach(() => {
  refresh.mockReset();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("PublicUpdatePanel composer", () => {
  it("starts empty: nothing from the private report is prefilled", () => {
    mount();
    expect((screen.getByLabelText(/^Public statement/) as HTMLTextAreaElement).value).toBe("");
    expect(screen.getByText(/Write neutrally/)).toBeTruthy();
  });

  it("refuses to draft, and says why, unless the report is verified and approved citations exist", () => {
    mount({ reportVerified: false });
    expect(screen.getByText(en.reviewer.publication.needsVerified)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Create a preview" })).toBeNull();
    cleanup();
    mount({ options: [] });
    expect(screen.getByText(en.reviewer.publication.noCitations)).toBeTruthy();
    cleanup();
    mount({ options: undefined });
    expect(screen.getByText(en.reviewer.publication.citationsUnavailable)).toBeTruthy();
  });

  it("checks the statement, date, and citations before sending anything", async () => {
    const fetcher = vi.fn();

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Create a preview" }));
    expect(await screen.findByText("Write the public statement.")).toBeTruthy();
    expect(screen.getByText("Choose the date this applies from.")).toBeTruthy();
    expect(screen.getByText("Choose at least one approved citation.")).toBeTruthy();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("sends the chosen passages verbatim and shows the exact public entry, with nothing public yet", async () => {
    const fetcher = vi.fn().mockResolvedValue(json(preview(), 201));

    vi.stubGlobal("fetch", fetcher);
    mount();
    await fillAndPreview(userEvent.setup());

    const frame = await screen.findByRole("heading", { name: "Exact preview" });
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(frame).toBeTruthy();
    expect(url).toBe(`/api/reviewer/reports/${REPORT}/public-updates`);
    expect(JSON.parse(String(init.body))).toEqual({
      statement: "Works were recorded as planned.",
      effective_on: "2026-09-01",
      verification_state: "verified_official",
      citations: [
        {
          source_version_id: uuid(901),
          passage: "The works are planned for the synthetic council.",
          location_label: "Page 2"
        }
      ]
    });
    const entry = document.querySelector(
      "[data-slot=public-preview-frame] [data-slot=timeline-item]"
    );

    expect(entry?.textContent).toContain("Works were recorded as planned.");
    expect(entry?.getAttribute("data-origin")).toBe("official");
    expect(screen.getByText(/Nothing is public yet/)).toBeTruthy();
    expect(screen.getByText("The works are planned for the synthetic council.")).toBeTruthy();
    expect(JSON.stringify({ ...window.localStorage, ...window.sessionStorage })).toBe("{}");
  });

  it("blocks publishing and lists the issues when the API says the text cannot be published", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        json(
          preview({
            can_publish: false,
            issues: [
              { field: "statement", code: "unsupported_term_corrupt" },
              { field: "statement", code: "report_text" }
            ]
          }),
          201
        )
      )
    );
    mount();
    const user = userEvent.setup();

    await fillAndPreview(user);
    const alert = await screen.findByRole("alert");

    expect(alert.textContent).toContain(
      "The word “corrupt” is used, but no cited passage contains it."
    );
    expect(alert.textContent).toContain("repeats wording from the private report");
    await user.click(screen.getByRole("button", { name: "Publish this update" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(
      screen.getByRole("button", { name: "Publish this update" }).getAttribute("aria-disabled")
    ).toBe("true");
  });

  it("publishes only after confirmation and sends nothing but the digest", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(preview(), 201))
      .mockResolvedValueOnce(
        json({
          public_update_id: uuid(1),
          project_slug: "synthetic-project-20",
          published_at: "2026-09-20T10:00:00Z"
        })
      );

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await fillAndPreview(user);
    await user.click(await screen.findByRole("button", { name: "Publish this update" }));
    const dialog = await screen.findByRole("alertdialog");

    expect(within(dialog).getByText(/exactly as shown in the preview/)).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(1);
    await user.click(within(dialog).getByRole("button", { name: "Publish" }));

    await screen.findByText(
      "This update is now on the project's public timeline exactly as previewed."
    );
    const [url, init] = fetcher.mock.calls[1] as [string, RequestInit];

    expect(url).toBe(`/api/reviewer/reports/${REPORT}/public-updates/${uuid(1)}/publish`);
    expect(JSON.parse(String(init.body))).toEqual({ preview_digest: "b".repeat(64) });
    expect(
      screen.getByRole("link", { name: "See it on the public record" }).getAttribute("href")
    ).toBe("/en/projects/synthetic-project-20");
  });

  it("returns to editing with an explanation when the preview is stale, publishing nothing", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(preview(), 201))
        .mockResolvedValueOnce(problem("preview_stale", 409))
    );
    mount();
    const user = userEvent.setup();

    await fillAndPreview(user);
    await user.click(await screen.findByRole("button", { name: "Publish this update" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Publish" })
    );

    expect(
      await screen.findByText(/changed after it was made, so it was not published/)
    ).toBeTruthy();
    expect(screen.getByLabelText(/^Public statement/)).toBeTruthy();
    expect((screen.getByLabelText(/^Public statement/) as HTMLTextAreaElement).value).toBe(
      "Works were recorded as planned."
    );
  });

  it("discards a draft only after confirmation", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(preview(), 201))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await fillAndPreview(user);
    await user.click(await screen.findByRole("button", { name: "Discard this draft" }));
    expect(fetcher).toHaveBeenCalledTimes(1);
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Discard draft" })
    );
    expect(await screen.findByText("The draft was discarded. Nothing was published.")).toBeTruthy();
    const [url] = fetcher.mock.calls[1] as [string, RequestInit];

    expect(url).toBe(`/api/reviewer/reports/${REPORT}/public-updates/${uuid(1)}/withdraw`);
  });

  it("opens an earlier draft's preview on request and offers no action for a published one", async () => {
    const fetcher = vi.fn().mockResolvedValue(json(preview()));

    vi.stubGlobal("fetch", fetcher);
    mount({
      drafts: [
        { id: uuid(1), state: "draft", createdAt: "2026-09-19T09:00:00Z" },
        { id: uuid(3), state: "published", createdAt: "2026-09-18T09:00:00Z" }
      ]
    });
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getAllByRole("button", { name: "Open preview" })).toHaveLength(1);
    await userEvent.setup().click(screen.getByRole("button", { name: "Open preview" }));

    expect(await screen.findByRole("heading", { name: "Exact preview" })).toBeTruthy();
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe(`/api/reviewer/reports/${REPORT}/public-updates/${uuid(1)}`);
    expect(init.method).toBe("GET");
  });

  it("refuses a malformed preview response and offers sign-in when the session ended", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ update: {} }, 201)));
    mount();
    const user = userEvent.setup();

    await fillAndPreview(user);
    expect((await screen.findByRole("alert")).textContent).toContain(en.problems.codes.internal);
    cleanup();

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("unauthenticated", 401)));
    mount();
    await fillAndPreview(user);
    expect((await screen.findByRole("alert")).textContent).toContain(
      en.reviewer.actions.sessionEnded
    );
    await waitFor(() => expect(refresh).not.toHaveBeenCalled());
  });
});
