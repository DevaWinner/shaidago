import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DiscoveryPreview } from "@/components/reviewer/discovery-preview";
import en from "../../messages/en.json";

const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000001";
const DIGEST = "a".repeat(64);
const shared = {
  actions: en.reviewer.actions,
  copy: en.reviewer.detail.scout,
  locale: "en",
  problems: en.problems,
  reportId: REPORT,
  signInHref: "/en/reviewer/sign-in?reason=expired"
};
const plan = {
  plan_digest: DIGEST,
  policy_version: "fictional-policy-v1",
  query: "Abuja AMAC public works official source",
  terms: [{ text: "Abuja", source: "project locality" }],
  rejected: [{ source: "report description", reason: "private report text is never searched" }]
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("DiscoveryPreview", () => {
  it("shows a bounded plan before confirmation and never posts report text", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(plan), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ run_id: REPORT, status: "searching", version: 1 }), {
          status: 201
        })
      );
    vi.stubGlobal("fetch", fetcher);
    render(<DiscoveryPreview {...shared} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Optional public search terms"), " public works ");
    await user.click(screen.getByRole("button", { name: "Prepare query for review" }));
    expect(await screen.findByText("Review the exact outbound query")).toBeTruthy();
    expect(screen.getByLabelText("Outbound query")).toHaveValue(plan.query);
    expect(screen.getByText(/report description/)).toBeTruthy();
    expect(JSON.parse(String(fetcher.mock.calls[0]?.[1]?.body))).toEqual({
      concepts: ["public works"]
    });

    await user.click(screen.getByRole("button", { name: "Approve and start search" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", {
        name: "Approve and start"
      })
    );
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    const [url, init] = fetcher.mock.calls[1] as [string, RequestInit];
    expect(url).toBe(`/api/reviewer/reports/${REPORT}/discovery`);
    expect(JSON.parse(String(init.body))).toEqual({
      approved_digest: DIGEST,
      concepts: ["public works"]
    });
    expect(screen.getByText(/Source search started/)).toBeTruthy();
    expect(JSON.stringify({ ...window.localStorage, ...window.sessionStorage })).toBe("{}");
  });

  it("discards a plan when a reviewer changes a term, requiring a new exact query", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(plan), { status: 200 }))
    );
    render(<DiscoveryPreview {...shared} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Prepare query for review" }));
    await screen.findByText("Review the exact outbound query");
    await user.type(screen.getByLabelText("Optional public search terms"), "council budget");
    expect(screen.queryByText("Review the exact outbound query")).toBeNull();
  });
});
