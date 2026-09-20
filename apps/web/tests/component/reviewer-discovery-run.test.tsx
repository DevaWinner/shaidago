import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DiscoveryRun } from "@/components/reviewer/discovery-run";
import en from "../../messages/en.json";
import { analysisFor, defaultSources } from "../support/mock-discovery.mjs";

const RUN = "0198f1a2-7b3c-4d4e-8f5a-d00000000001";
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const problem = (code: string, status: number) =>
  new Response(JSON.stringify({ code, status }), {
    status,
    headers: { "Content-Type": "application/problem+json" }
  });

function run(over: Record<string, unknown> = {}) {
  const sources = defaultSources("e1", true);

  return {
    run_id: RUN,
    report_id: "0198f1a2-7b3c-4d4e-8f5a-000000000001",
    scope: "reviewer",
    status: "needs_review",
    version: 2,
    created_at: "2026-09-20T09:00:00Z",
    finished_at: "2026-09-20T09:01:00Z",
    demo_replay: true,
    failure_code: null,
    query_text: "q",
    results_found: 3,
    fetched_count: 3,
    analysed_count: 3,
    cancel_requested: false,
    sources,
    analysis: analysisFor(sources),
    ...over
  };
}

const mount = (id = RUN) =>
  render(
    <DiscoveryRun
      actions={en.reviewer.actions}
      copy={en.discovery}
      locale="en"
      problems={en.problems}
      runId={id}
      signInHref="/en/reviewer/sign-in?reason=expired"
    />
  );

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("DiscoveryRun results", () => {
  it("labels every card as not yet reviewed, groups the repeat, flags the instruction, and drops the unsafe link", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(run())));
    mount();
    await screen.findByText("Discovered sources");

    const cards = document.querySelectorAll("[data-slot=discovery-source]");

    expect(cards).toHaveLength(3);
    for (const card of cards) {
      expect(card.textContent).toContain("discovered — not yet reviewed");
    }
    expect(
      document.querySelectorAll("[data-slot=discovery-duplicates] [data-slot=discovery-source]")
    ).toHaveLength(1);
    expect(screen.getByText(/tries to give instructions/)).toBeTruthy();
    expect(screen.getByText(/could not be shown safely/)).toBeTruthy();
    expect(document.querySelectorAll("a[href^='javascript']")).toHaveLength(0);
    expect(document.querySelector("script")).toBeNull();
    expect(
      screen
        .getAllByRole("link", { name: "Open the original page (new tab)" })[0]
        ?.getAttribute("rel")
    ).toContain("noopener");
  });

  it("keeps analysis categories separate, links citations to cards, and shows no score", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(run())));
    mount();
    await screen.findByText("Analysis (an explanation, not a source)");

    expect(document.querySelector("[data-section=facts]")?.textContent).toContain(
      "public works update"
    );
    expect(document.querySelector("[data-section=claims]")?.textContent).toContain(
      "example.test says:"
    );
    expect(document.querySelector("[data-section=contradictions]")?.textContent).toContain(
      "different fictional dates"
    );
    expect(document.querySelector("[data-section=gaps]")?.textContent).toContain(
      "No completion date"
    );
    expect(document.querySelector("[data-section=safety]")?.textContent).toContain("human review");
    const link = within(document.querySelector("[data-section=facts]") as HTMLElement).getByRole(
      "link"
    );

    expect(document.querySelector(link.getAttribute("href") as string)).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/confidence:|score:|rank #|\d+ ?%/i);
  });

  it("shows no analysis when it cannot be checked, but still shows the sources", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          json(run({ analysis: analysisFor(defaultSources("e1", true), { invalid: true }) }))
        )
    );
    mount();
    await screen.findByText(/No analysis is shown/);
    expect(document.querySelectorAll("[data-slot=discovery-source]")).toHaveLength(3);
    expect(screen.queryByText("Supported facts")).toBeNull();
  });

  it("refuses a run that is not the one it was given, or that is malformed", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(json(run({ run_id: "0198f1a2-7b3c-4d4e-8f5a-d00000000009" })))
    );
    mount();
    expect((await screen.findByRole("alert")).textContent).toContain(en.problems.codes.internal);
    expect(document.querySelectorAll("[data-slot=discovery-source]")).toHaveLength(0);
  });

  it("says why a run failed, or was cancelled, and what is still shown", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        json(
          run({
            status: "failed",
            failure_code: "provider_unavailable",
            sources: [],
            analysis: null
          })
        )
      )
    );
    mount();
    expect(await screen.findByText("The search provider was unavailable.")).toBeTruthy();
    expect(screen.getByText(en.discovery.failure.empty)).toBeTruthy();
    cleanup();

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        json(
          run({
            status: "cancelled",
            sources: defaultSources("e1", true).slice(0, 1),
            analysis: null
          })
        )
      )
    );
    mount();
    expect(await screen.findByText(en.discovery.states.cancelledPartial)).toBeTruthy();
  });

  it("offers a retry after an outage and recovers", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(problem("dependency_unavailable", 503))
      .mockResolvedValue(json(run()));

    vi.stubGlobal("fetch", fetcher);
    mount();
    await userEvent.setup().click(await screen.findByRole("button", { name: "Check again" }));
    expect(await screen.findByText("Discovered sources")).toBeTruthy();
  });
});

describe("DiscoveryRun actions", () => {
  it("cancels only after confirmation", async () => {
    const active = run({
      status: "searching",
      version: 1,
      finished_at: null,
      sources: [],
      analysis: null,
      results_found: 0,
      fetched_count: 0,
      analysed_count: 0
    });
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(active))
      .mockResolvedValueOnce(json({ status: "cancelled" }))
      .mockResolvedValue(
        json(run({ status: "cancelled", version: 2, sources: [], analysis: null }))
      );

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Cancel this run" }));
    expect(fetcher).toHaveBeenCalledTimes(1);
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancel the run" })
    );
    await waitFor(() =>
      expect(fetcher.mock.calls[1]?.[0]).toBe(`/api/reviewer/discovery/${RUN}/cancel`)
    );
    expect((fetcher.mock.calls[1] as [string, RequestInit])[1].body).toBeNull();
    expect(await screen.findByText(en.discovery.states.cancelledEmpty)).toBeTruthy();
  });

  it("records an approval or a rejection only after confirmation", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(run()))
      .mockResolvedValueOnce(json({ status: "complete" }))
      .mockResolvedValue(json(run({ status: "complete", version: 3 })));

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Approve completion" }));
    expect(fetcher).toHaveBeenCalledTimes(1);
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", {
        name: "Record decision"
      })
    );
    await waitFor(() =>
      expect(fetcher.mock.calls[1]?.[0]).toBe(`/api/reviewer/discovery/${RUN}/review`)
    );
    expect(JSON.parse(String((fetcher.mock.calls[1] as [string, RequestInit])[1].body))).toEqual({
      command: "approve_completion"
    });
  });

  it("stops asking for polling controls once the run is terminal", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(run({ status: "complete" }))));
    mount();
    await screen.findByText("Discovered sources");
    expect(screen.queryByRole("button", { name: "Stop checking" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Cancel this run" })).toBeNull();
  });
});

describe("follow-up questions", () => {
  it("sends an answer in a POST body only, keeps nothing afterwards, and shows a safe acknowledgement", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(run()))
      .mockResolvedValue(json({ acknowledged: true }));

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();
    const first = (await screen.findAllByRole("listitem")).find(
      (item) => item.getAttribute("data-slot") === "discovery-follow-up"
    ) as HTMLElement;

    await user.type(within(first).getByLabelText("Your answer (private)"), "PRIVATE-ANSWER-CANARY");
    await user.click(within(first).getByRole("button", { name: "Send answer" }));

    await within(first).findByText("Recorded. What you typed is not shown again.");
    const [url, init] = fetcher.mock.calls[1] as [string, RequestInit];

    expect(url).toBe(`/api/reviewer/discovery/${RUN}/follow-up-answers`);
    expect(JSON.parse(String(init.body))).toEqual({
      question_index: 0,
      kind: "answered",
      answer: "PRIVATE-ANSWER-CANARY"
    });
    expect(document.body.textContent).not.toContain("PRIVATE-ANSWER-CANARY");
    expect(JSON.stringify({ ...window.localStorage, ...window.sessionStorage })).toBe("{}");
  });

  it("caps at five, lets a question be skipped or flagged, and needs text to answer", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(run()))
      .mockResolvedValue(json({ acknowledged: true }));

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await screen.findByText("At most 5 questions are shown.");
    const items = document.querySelectorAll<HTMLElement>("[data-slot=discovery-follow-up]");

    expect(items.length).toBeLessThanOrEqual(5);
    await user.click(within(items[0] as HTMLElement).getByRole("button", { name: "Send answer" }));
    expect(
      await within(items[0] as HTMLElement).findByText("Write an answer or choose Skip.")
    ).toBeTruthy();
    await user.click(
      within(items[1] as HTMLElement).getByRole("button", { name: "Mark as unsafe to ask" })
    );
    await within(items[1] as HTMLElement).findByText("Marked unsafe.");
    expect(JSON.parse(String((fetcher.mock.calls[1] as [string, RequestInit])[1].body))).toEqual({
      question_index: 1,
      kind: "unsafe"
    });
  });
});

describe("source decisions", () => {
  it("needs a reason and a confirmation, and says attaching does not verify anything", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(run()))
      .mockResolvedValueOnce(json({ disposition: "attached" }))
      .mockResolvedValue(json(run()));

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();
    const card = (await screen.findAllByText("Decision: Not reviewed"))[0]?.closest(
      "[data-slot=discovery-decision]"
    ) as HTMLElement;

    await user.click(within(card).getByRole("button", { name: "Attach as a pending source" }));
    expect(await within(card).findByText("Give a reason.")).toBeTruthy();
    await user.type(within(card).getByLabelText("Reason"), "Matches the record.");
    await user.click(within(card).getByRole("button", { name: "Attach as a pending source" }));
    const dialog = await screen.findByRole("alertdialog");

    expect(within(dialog).getByText(/does not approve any fact or publish anything/)).toBeTruthy();
    expect(fetcher).toHaveBeenCalledTimes(1);
    await user.click(within(dialog).getByRole("button", { name: "Record decision" }));
    await waitFor(() =>
      expect(fetcher.mock.calls[1]?.[0]).toMatch(
        /\/api\/reviewer\/discovered-sources\/.+\/decision$/
      )
    );
    expect(JSON.parse(String((fetcher.mock.calls[1] as [string, RequestInit])[1].body))).toEqual({
      command: "attach",
      reason: "Matches the record."
    });
  });

  it("offers only the decisions the state machine allows, and a conflict reloads the run", async () => {
    const sources = defaultSources("e1", true).map((source, index) => ({
      ...source,
      disposition: index === 0 ? "attached" : "not_reviewed"
    }));
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(json(run({ sources, analysis: analysisFor(sources) })))
      .mockResolvedValueOnce(problem("conflict", 409))
      .mockResolvedValue(json(run({ sources, analysis: analysisFor(sources) })));

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();
    const attached = (await screen.findByText(/Decision: Attached as a pending source/)).closest(
      "[data-slot=discovery-decision]"
    ) as HTMLElement;

    expect(within(attached).getByRole("button", { name: "Reconsider" })).toBeTruthy();
    expect(within(attached).queryByRole("button", { name: "Reject" })).toBeNull();
    await user.type(within(attached).getByLabelText("Reason"), "Changed my mind.");
    await user.click(within(attached).getByRole("button", { name: "Reconsider" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", {
        name: "Record decision"
      })
    );
    expect(await screen.findByText(/changed since you loaded it/)).toBeTruthy();
    await waitFor(() => expect(fetcher.mock.calls.length).toBeGreaterThanOrEqual(3));
  });
});
