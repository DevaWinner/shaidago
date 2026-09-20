import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { StatusActions } from "@/components/reviewer/status-actions";
import en from "../../messages/en.json";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000001";
const problem = (code: string, status: number) =>
  new Response(JSON.stringify({ code, status }), {
    status,
    headers: { "Content-Type": "application/problem+json" }
  });
const ok = () =>
  new Response(JSON.stringify({ status: "under_review", version: 3, published: false }), {
    status: 200
  });

const mount = (status = "received", version = 2) =>
  render(
    <StatusActions
      actions={en.reviewer.actions}
      copy={en.reviewer.transition}
      locale="en"
      problems={en.problems}
      reportId={REPORT}
      signInHref="/en/reviewer/sign-in?reason=expired"
      status={status}
      statuses={en.reviewer.queue.statuses}
      version={version}
    />
  );
const commands = () =>
  within(screen.getByLabelText("Action"))
    .getAllByRole("option")
    .map((option) => option.textContent);

beforeEach(() => {
  refresh.mockReset();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("StatusActions", () => {
  it("offers only the commands the contract allows from the current status", () => {
    mount("received");
    expect(commands()).toEqual([
      "Start review",
      "Ask the reporter for more information",
      "Close the report"
    ]);
    cleanup();
    mount("closed");
    expect(commands()).toEqual(["Reopen the report"]);
    cleanup();
    mount("verified_for_public_update");
    expect(commands()).toEqual(["Resume review", "Record a referral", "Close the report"]);
  });

  it("offers nothing for a status it does not know", () => {
    mount("published");
    expect(screen.getByText(en.reviewer.transition.none)).toBeTruthy();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("says what changes, and that nothing is published, before anything is sent", async () => {
    const fetcher = vi.fn();

    vi.stubGlobal("fetch", fetcher);
    mount("under_review");
    const user = userEvent.setup();

    await user.selectOptions(screen.getByLabelText("Action"), "close");
    expect(screen.getByText("Moves the report from Under review to Closed.")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Apply change" }));
    const dialog = await screen.findByRole("alertdialog");

    expect(within(dialog).getByText(/does not publish anything on the public record/)).toBeTruthy();
    expect(within(dialog).getByText(/Check the message before you confirm/)).toBeTruthy();
    expect(within(dialog).getByText("Change the status to Closed?")).toBeTruthy();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("requires a message to ask for information and a reason to reopen", async () => {
    mount("received");
    const user = userEvent.setup();

    await user.selectOptions(screen.getByLabelText("Action"), "request_information");
    await user.click(screen.getByRole("button", { name: "Apply change" }));
    expect(await screen.findByText("Say what you need from the reporter.")).toBeTruthy();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    cleanup();

    mount("closed");
    await user.click(screen.getByRole("button", { name: "Apply change" }));
    expect(await screen.findByText("Give a reason for reopening.")).toBeTruthy();
  });

  it("sends the status and version it was shown with, announces the result, and refreshes", async () => {
    const fetcher = vi.fn().mockResolvedValue(ok());

    vi.stubGlobal("fetch", fetcher);
    mount("received", 2);
    const user = userEvent.setup();

    await user.type(
      screen.getByLabelText("Message the reporter will see"),
      " Please send a photo "
    );
    await user.click(screen.getByRole("button", { name: "Apply change" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Apply change" })
    );

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe(`/api/reviewer/reports/${REPORT}/status-transition`);
    expect(JSON.parse(String(init.body))).toEqual({
      command: "start_review",
      expected_status: "received",
      expected_version: 2,
      reporter_message: "Please send a photo"
    });
    expect(
      screen.getByText("Status changed from Received to Under review. Nothing was published.")
    ).toBeTruthy();
    expect(
      (screen.getByLabelText("Message the reporter will see") as HTMLTextAreaElement).value
    ).toBe("");
  });

  it("locks while a request is pending so a second press cannot send twice", async () => {
    let release: (value: Response) => void = () => undefined;
    const fetcher = vi
      .fn()
      .mockReturnValue(new Promise<Response>((resolve) => (release = resolve)));

    vi.stubGlobal("fetch", fetcher);
    mount("received");
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Apply change" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Apply change" })
    );
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));

    expect(screen.getByRole("button", { name: "Applying" }).getAttribute("aria-disabled")).toBe(
      "true"
    );
    expect(screen.getByLabelText("Action").closest("fieldset")?.disabled).toBe(true);
    release(ok());
    await waitFor(() => expect(refresh).toHaveBeenCalledTimes(1));
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("explains a conflict, keeps what was typed, and reloads only when asked", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("report_version_conflict", 409)));
    mount("received");
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Internal reason (private)"), "Because");
    await user.click(screen.getByRole("button", { name: "Apply change" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Apply change" })
    );

    const alert = await screen.findByRole("alert");

    expect(alert.textContent).toContain("changed while you were working");
    expect((screen.getByLabelText("Internal reason (private)") as HTMLTextAreaElement).value).toBe(
      "Because"
    );
    expect(refresh).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Reload the report" }));
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("offers sign-in when the session ended and a reviewed message for other failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("unauthenticated", 401)));
    mount("received");
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Apply change" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Apply change" })
    );
    expect((await screen.findByRole("alert")).textContent).toContain(
      en.reviewer.actions.sessionEnded
    );
    expect(screen.getByRole("link", { name: "Sign in again" })).toBeTruthy();
    cleanup();

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    mount("received");
    await user.click(screen.getByRole("button", { name: "Apply change" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Apply change" })
    );
    expect((await screen.findByRole("alert")).textContent).toContain(en.problems.mayHaveCompleted);
  });
});
