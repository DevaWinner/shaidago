import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProjectDiscovery } from "@/components/project/project-discovery";
import en from "../../messages/en.json";

const run = {
  created_at: "2026-09-20T09:00:00Z",
  demo_replay: true,
  progress: { analysed: 2, fetched: 3, results_found: 3 },
  run_id: "00000000-0000-4000-8000-000000000801",
  status: "complete",
  version: 2
};
const response = (body: unknown) =>
  new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status: 200
  });

function view() {
  return render(
    <ProjectDiscovery
      copy={en.project.discovery}
      locale="en"
      problems={en.problems}
      resultsCopy={en.discovery}
      slug="synthetic-record-full"
    />
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("ProjectDiscovery", () => {
  it("starts through the same-origin BFF and renders the returned replay run without a progress percentage", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response({ action: "show_latest_completed", run_id: run.run_id }))
      .mockResolvedValueOnce(response(run));
    vi.stubGlobal("fetch", fetch);
    const user = userEvent.setup();
    view();

    await user.click(screen.getByRole("button", { name: en.project.discovery.start }));

    await screen.findAllByText(en.project.discovery.states.complete);
    expect(screen.getByText("Found 3; fetched 3; analysed 2.")).toBeTruthy();
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(fetch.mock.calls[0]?.[0]).toBe("/api/public/discovery");
    expect(fetch.mock.calls[0]?.[1]?.body).toBe('{"slug":"synthetic-record-full"}');
    expect(fetch.mock.calls[1]?.[0]).toBe(`/api/public/discovery/${run.run_id}`);
  });

  it("shows the safe unavailable state when the API does not supply a run", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(response({ action: "unavailable", run_id: null }))
    );
    const user = userEvent.setup();
    view();

    await user.click(screen.getByRole("button", { name: en.project.discovery.start }));

    await screen.findByText(en.project.discovery.unavailable);
  });

  it("fails closed when a run response has no usable progress shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(response({ action: "create", run_id: run.run_id }))
        .mockResolvedValueOnce(response({ run_id: run.run_id, status: "complete" }))
    );
    const user = userEvent.setup();
    view();

    await user.click(screen.getByRole("button", { name: en.project.discovery.start }));

    await waitFor(() => expect(screen.getAllByText(en.problems.codes.internal)).toHaveLength(2));
  });
});
