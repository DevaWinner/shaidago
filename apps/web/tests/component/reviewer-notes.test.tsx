import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvidenceDownload } from "@/components/reviewer/evidence-download";
import { NoteForm } from "@/components/reviewer/note-form";
import { AskQuestionForm, WithdrawQuestionButton } from "@/components/reviewer/question-controls";
import { NotesSection, detailContext } from "@/components/reviewer/report-detail";
import en from "../../messages/en.json";

const refresh = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000001";
const shared = {
  actions: en.reviewer.actions,
  locale: "en",
  problems: en.problems,
  reportId: REPORT,
  signInHref: "/en/reviewer/sign-in?reason=expired"
};
const problem = (code: string, status: number) =>
  new Response(JSON.stringify({ code, status }), {
    status,
    headers: { "Content-Type": "application/problem+json" }
  });

beforeEach(() => {
  refresh.mockReset();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("NoteForm", () => {
  const mount = () => render(<NoteForm {...shared} copy={en.reviewer.notes} />);

  it("needs text, then an explicit confirmation, and sends nothing before it", async () => {
    const fetcher = vi.fn();

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText("Write a note first.")).toBeTruthy();
    await user.type(screen.getByLabelText("New note"), "A private note");
    await user.click(screen.getByRole("button", { name: "Add note" }));

    const dialog = await screen.findByRole("alertdialog");

    expect(within(dialog).getByText(/cannot be edited or deleted afterwards/)).toBeTruthy();
    expect(fetcher).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    expect(fetcher).not.toHaveBeenCalled();
    expect((screen.getByLabelText("New note") as HTMLTextAreaElement).value).toBe("A private note");
  });

  it("posts the note as JSON to the report's handler, clears the box, refreshes, and stores nothing", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ note_id: "n" }), { status: 201 }));

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("New note"), "  A private note  ");
    await user.click(screen.getByRole("button", { name: "Add note" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Add note" })
    );

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe(`/api/reviewer/reports/${REPORT}/notes`);
    expect(JSON.parse(String(init.body))).toEqual({ body: "A private note" });
    expect((screen.getByLabelText("New note") as HTMLTextAreaElement).value).toBe("");
    expect(screen.getByText("Note added.")).toBeTruthy();
    expect(JSON.stringify({ ...window.localStorage, ...window.sessionStorage })).toBe("{}");
  });

  it("keeps the text after a failure and warns that it may have been saved when the connection dropped", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    mount();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("New note"), "Keep me");
    await user.click(screen.getByRole("button", { name: "Add note" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Add note" })
    );

    const alert = await screen.findByRole("alert");

    expect(alert.textContent).toContain(en.problems.mayHaveCompleted);
    expect((screen.getByLabelText("New note") as HTMLTextAreaElement).value).toBe("Keep me");
    expect(refresh).not.toHaveBeenCalled();
  });

  it("offers sign-in when the session ended and shows a reviewed message for markup", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("unauthenticated", 401)));
    mount();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("New note"), "x");
    await user.click(screen.getByRole("button", { name: "Add note" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Add note" })
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      en.reviewer.actions.sessionEnded
    );
    expect(screen.getByRole("link", { name: "Sign in again" }).getAttribute("href")).toBe(
      shared.signInHref
    );
    cleanup();

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("markup_not_allowed", 422)));
    mount();
    await user.type(screen.getByLabelText("New note"), "<b>x</b>");
    await user.click(screen.getByRole("button", { name: "Add note" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Add note" })
    );
    expect((await screen.findByRole("alert")).textContent).toContain(
      en.problems.codes.markupNotAllowed
    );
  });

  it("refuses a note over the limit before asking for confirmation", async () => {
    mount();
    const box = screen.getByLabelText("New note") as HTMLTextAreaElement;
    const user = userEvent.setup();

    await user.click(box);
    await user.paste("x".repeat(4050));
    await user.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText("This note is too long.")).toBeTruthy();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });
});

describe("AskQuestionForm and WithdrawQuestionButton", () => {
  it("checks the length, confirms, and posts the question", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ question_id: "q" }), { status: 201 }));

    vi.stubGlobal("fetch", fetcher);
    render(<AskQuestionForm {...shared} copy={en.reviewer.questionActions} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("New question for the reporter"), "abc");
    await user.click(screen.getByRole("button", { name: "Ask question" }));
    expect(await screen.findByText("Write at least 5 characters.")).toBeTruthy();
    await user.type(screen.getByLabelText("New question for the reporter"), "def");
    await user.click(screen.getByRole("button", { name: "Ask question" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Send question" })
    );

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe(`/api/reviewer/reports/${REPORT}/follow-up-questions`);
    expect(JSON.parse(String(init.body))).toEqual({ question: "abcdef" });
  });

  it("withdraws only after confirmation, with an empty body, and names the question", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));

    vi.stubGlobal("fetch", fetcher);
    render(
      <WithdrawQuestionButton
        {...shared}
        copy={en.reviewer.questionActions}
        question="Which side?"
        questionId="0198f1a2-7b3c-4d4e-8f5a-f00000000002"
      />
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Withdraw the question: Which side?" }));
    expect(fetcher).not.toHaveBeenCalled();
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", {
        name: "Withdraw question"
      })
    );

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe(
      `/api/reviewer/reports/${REPORT}/follow-up-questions/0198f1a2-7b3c-4d4e-8f5a-f00000000002/withdraw`
    );
    expect(init.body).toBeNull();
  });
});

describe("EvidenceDownload", () => {
  const mount = () =>
    render(
      <EvidenceDownload
        actions={en.reviewer.actions}
        copy={en.reviewer.download}
        evidenceId="0198f1a2-7b3c-4d4e-8f5a-a00000000001"
        fileName="evidence-1.jpg"
        problems={en.problems}
        reportId={REPORT}
        signInHref="/en/reviewer/sign-in?reason=expired"
      />
    );

  it("makes no request until asked, then a fresh one per press, and releases the bytes", async () => {
    const fetcher = vi
      .fn()
      .mockImplementation(() => Promise.resolve(new Response("bytes", { status: 200 })));
    const create = vi.fn().mockReturnValue("blob:fictional");
    const revoke = vi.fn();

    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: create, revokeObjectURL: revoke }));
    mount();
    expect(fetcher).not.toHaveBeenCalled();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Download evidence-1.jpg" }));
    await screen.findByText("The download of evidence-1.jpg started.");
    await user.click(screen.getByRole("button", { name: "Download evidence-1.jpg" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));

    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe(
      `/api/reviewer/reports/${REPORT}/evidence/0198f1a2-7b3c-4d4e-8f5a-a00000000001`
    );
    expect(init.cache).toBe("no-store");
    await waitFor(() => expect(revoke).toHaveBeenCalledWith("blob:fictional"));
  });

  it("says why it failed, offers sign-in when the session ended, and stores nothing", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("unauthenticated", 401)));
    mount();
    await userEvent.setup().click(screen.getByRole("button", { name: "Download evidence-1.jpg" }));

    const status = await screen.findByText(/could not be downloaded/);

    expect(status.textContent).toContain("Your session ended");
    expect(screen.getByRole("link", { name: "Sign in again" })).toBeTruthy();
    expect(JSON.stringify({ ...window.localStorage, ...window.sessionStorage })).toBe("{}");
  });

  it("says the service is unreachable when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    mount();
    await userEvent.setup().click(screen.getByRole("button", { name: "Download evidence-1.jpg" }));

    expect((await screen.findByText(/could not be downloaded/)).textContent).toContain(
      en.problems.codes.network
    );
  });
});

describe("NotesSection", () => {
  const context = detailContext(en.reviewer.detail, en.reviewer.queue, "en", "en");
  const note = (over: Record<string, unknown> = {}) => ({
    note_id: "1",
    created_at: "2026-09-10T09:00:00Z",
    author: "reviewer-demo",
    body: "Plain <b>text</b>",
    ...over
  });

  it("renders notes as escaped text, oldest first, with a note whose key is gone", () => {
    const { container } = render(
      <NotesSection
        context={context}
        form={<p>form</p>}
        notes={{
          state: "ok",
          items: [note(), note({ note_id: "2", body: null })],
          nextHref: "/x?notes=2#notes",
          firstHref: undefined
        }}
        words={en.reviewer.notes}
      />
    );

    expect(container.querySelector("b")).toBeNull();
    expect(screen.getByText("Plain <b>text</b>")).toBeTruthy();
    expect(screen.getByText("The text of this note is no longer available.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Show later notes" }).getAttribute("href")).toBe(
      "/x?notes=2#notes"
    );
  });

  it("says when there are none and keeps the form when the list could not load", () => {
    const { rerender } = render(
      <NotesSection
        context={context}
        form={<p>form</p>}
        notes={{ state: "ok", items: [], nextHref: undefined, firstHref: undefined }}
        words={en.reviewer.notes}
      />
    );

    expect(screen.getByText("No notes yet.")).toBeTruthy();
    rerender(
      <NotesSection
        context={context}
        form={<p>form</p>}
        notes={{ state: "unavailable", retryHref: "/x#notes" }}
        words={en.reviewer.notes}
      />
    );
    expect(screen.getByText(/could not be loaded/)).toBeTruthy();
    expect(screen.getByText("form")).toBeTruthy();
  });
});
