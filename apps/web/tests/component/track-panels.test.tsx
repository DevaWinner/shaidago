import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HandlePanel } from "@/components/track/handle-panel";
import { TrackPanel } from "@/components/track/track-panel";
import en from "../../messages/en.json";

const uuid = "0198f1a2-7b3c-4d4e-8f5a-123456789abc";
const status = (over: Record<string, unknown> = {}) => ({
  follow_up_questions: [],
  message: "Hello",
  next_action: "wait_for_review",
  status: "under_review",
  status_updated_at: "2026-09-19T09:00:00Z",
  ...over
});
const ok = (body: unknown, code = 200) =>
  new Response(code === 204 ? null : JSON.stringify(body), { status: code });
const problem = (code: string, status: number, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify({ code, status }), {
    status,
    headers: { "Content-Type": "application/problem+json", ...headers }
  });

const mountTrack = () =>
  render(
    <TrackPanel
      copy={en.track}
      language="en"
      locale="en"
      problems={en.problems}
      reportHref="/en/report"
    />
  );
const mountHandle = () =>
  render(<HandlePanel copy={en.handle} locale="en" problems={en.problems} trackHref="/en/track" />);

async function enabled(name: string | RegExp) {
  const button = await screen.findByRole("button", { name });
  await waitFor(() => expect(button.hasAttribute("disabled")).toBe(false));
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("TrackPanel", () => {
  it("looks a code up through a POST body only, normalises it, clears the box, and shows a public-safe status", async () => {
    const fetcher = vi.fn().mockResolvedValue(ok(status()));

    vi.stubGlobal("fetch", fetcher);
    mountTrack();
    await enabled(en.track.code.submit);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(en.track.code.label), "sg – demo 0001");
    await user.click(screen.getByRole("button", { name: en.track.code.submit }));

    const result = await screen.findByText(en.track.statuses.under_review.meaning);
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(result).toBeTruthy();
    expect(url).toBe("/api/tracking/lookup");
    expect(JSON.parse(String(init.body))).toEqual({ code: "sg-demo0001" });
    expect((screen.getByLabelText(en.track.code.label) as HTMLInputElement).value).toBe("");
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
    expect(document.body.textContent).not.toContain("demo0001");
    expect(screen.getByText(en.track.next.wait_for_review, { exact: false })).toBeTruthy();
  });

  it("gives one generic answer for an unknown code, and keeps what was typed", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("tracking_code_not_recognised", 404)));
    mountTrack();
    await enabled(en.track.code.submit);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(en.track.code.label), "whatever");
    await user.click(screen.getByRole("button", { name: en.track.code.submit }));

    expect(
      (await screen.findAllByText(en.problems.codes.codeNotRecognised)).length
    ).toBeGreaterThan(0);
    expect((screen.getByLabelText(en.track.code.label) as HTMLInputElement).value).toBe("whatever");
  });

  it("asks for a code before sending, and says how long to wait after a rate limit", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(problem("rate_limited", 429, { "Retry-After": "30" }));

    vi.stubGlobal("fetch", fetcher);
    mountTrack();
    await enabled(en.track.code.submit);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: en.track.code.submit }));
    expect(await screen.findByText(en.track.code.empty)).toBeTruthy();
    expect(fetcher).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText(en.track.code.label), "abc");
    await user.click(screen.getByRole("button", { name: en.track.code.submit }));
    expect(await screen.findByText("Try again in about 30 seconds.")).toBeTruthy();
  });

  it("answers a follow-up with one key per exact response, then shows the new state", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        ok(
          status({
            follow_up_questions: [{ question_id: uuid, state: "open", text: "When?" }],
            next_action: "answer_follow_up"
          })
        )
      )
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(ok({ acknowledged: true, question_state: "answered" }));

    vi.stubGlobal("fetch", fetcher);
    mountTrack();
    await enabled(en.track.code.submit);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(en.track.code.label), "code-1");
    await user.click(screen.getByRole("button", { name: en.track.code.submit }));
    await screen.findByText("When?");
    await user.click(screen.getByRole("button", { name: en.track.followUp.answer }));
    expect(await screen.findByText(en.track.followUp.answerEmpty)).toBeTruthy();
    await user.type(screen.getByLabelText(en.track.followUp.answerLabel), "Around noon.");
    await user.click(screen.getByRole("button", { name: en.track.followUp.answer }));
    await screen.findByText(en.problems.codes.network);
    await user.click(screen.getByRole("button", { name: en.track.followUp.answer }));

    expect(await screen.findByText(en.track.followUp.sent)).toBeTruthy();
    const [, first] = fetcher.mock.calls[1] as [string, RequestInit];
    const [, second] = fetcher.mock.calls[2] as [string, RequestInit];

    expect((first.headers as Record<string, string>)["Idempotency-Key"]).toBe(
      (second.headers as Record<string, string>)["Idempotency-Key"]
    );
    expect(JSON.parse(String(second.body))).toMatchObject({
      code: "code-1",
      answer: "Around noon.",
      kind: "answered"
    });
    expect(screen.getByText(en.track.followUp.states.answered)).toBeTruthy();
  });

  it("lists reports by handle, clears the passphrase, and treats a wrong or missing handle alike", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(problem("invalid_credentials", 403))
      .mockResolvedValueOnce(
        ok({
          reports: [
            {
              message: "m",
              next_action: "wait_for_review",
              status: "received",
              status_updated_at: "2026-09-19T09:00:00Z"
            }
          ]
        })
      );

    vi.stubGlobal("fetch", fetcher);
    mountTrack();
    await enabled(en.track.handle.submit);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: en.track.handle.submit }));
    expect(await screen.findByText(en.track.handle.emptyHandle)).toBeTruthy();
    await user.type(screen.getByLabelText(en.track.handle.handleLabel), "some-handle");
    await user.type(screen.getByLabelText(en.track.handle.passphraseLabel), "one two three");
    await user.click(screen.getByRole("button", { name: en.track.handle.submit }));
    expect(
      (await screen.findAllByText(en.problems.codes.invalidCredentials)).length
    ).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: en.track.handle.submit }));

    const result = document.querySelector("[data-slot=handle-result]") as HTMLElement;

    expect(
      await within(result).findByText(en.track.statuses.received.label, { exact: false })
    ).toBeTruthy();
    expect((screen.getByLabelText(en.track.handle.passphraseLabel) as HTMLInputElement).value).toBe(
      ""
    );
    expect(document.body.textContent).not.toContain("one two three");
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });

  it("does not call the handle a verified identity anywhere", () => {
    mountTrack();
    const text = document.body.textContent ?? "";

    expect(text).toContain("not an account or proof of who you are");
    expect(text).not.toMatch(/verified identity|your account|sign in|log in/i);
  });
});

describe("HandlePanel", () => {
  it("creates a handle with one key, shows it once, and clears it on request without storing it", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        ok(
          { handle: "fictional-handle-001", passphrase: "amber bridge candle", recoverable: false },
          201
        )
      );

    vi.stubGlobal("fetch", fetcher);
    mountHandle();
    await enabled(en.handle.create.button);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: en.handle.create.button }));
    expect(await screen.findByText("fictional-handle-001")).toBeTruthy();
    expect(screen.getByText("amber bridge candle")).toBeTruthy();
    expect(screen.getByText(en.handle.created.warning)).toBeTruthy();
    const init = fetcher.mock.calls[0]?.[1] as RequestInit;

    expect(init.body).toBeNull();
    expect((init.headers as Record<string, string>)["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
    await user.click(screen.getByRole("button", { name: en.handle.created.done }));
    expect(document.body.textContent).not.toContain("fictional-handle-001");
  });

  it("reuses the creation key after a lost answer, and never copies unless asked", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(ok({ handle: "h", passphrase: "p", recoverable: false }, 201));

    vi.stubGlobal("fetch", fetcher);
    mountHandle();
    await enabled(en.handle.create.button);
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    await user.click(screen.getByRole("button", { name: en.handle.create.button }));
    expect(await screen.findByText(en.problems.codes.network)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: en.handle.create.button }));
    await screen.findByText(en.handle.created.warning);

    const key = (i: number) =>
      ((fetcher.mock.calls[i]?.[1] as RequestInit).headers as Record<string, string>)[
        "Idempotency-Key"
      ];

    expect(key(0)).toBe(key(1));
    expect(writeText).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: en.handle.created.copy }));
    expect(writeText).toHaveBeenCalledWith("h\np");
  });

  it("explains deletion first, requires confirmation, and says the reports stay", async () => {
    const fetcher = vi.fn().mockResolvedValue(ok(null, 204));

    vi.stubGlobal("fetch", fetcher);
    mountHandle();
    await enabled(en.handle.delete.submit);
    const user = userEvent.setup();

    expect(screen.getByText(en.handle.delete.explain)).toBeTruthy();
    await user.type(screen.getByLabelText(en.handle.delete.handleLabel), "some-handle");
    await user.type(screen.getByLabelText(en.handle.delete.passphraseLabel), "secret words");
    await user.click(screen.getByRole("button", { name: en.handle.delete.submit }));
    expect(await screen.findByText(en.handle.delete.needConfirm)).toBeTruthy();
    expect(fetcher).not.toHaveBeenCalled();
    await user.click(screen.getByRole("checkbox", { name: /I understand the reports stay/ }));
    await user.click(screen.getByRole("button", { name: en.handle.delete.submit }));

    expect(await screen.findByText(en.handle.delete.done)).toBeTruthy();
    expect(
      (screen.getByLabelText(en.handle.delete.passphraseLabel) as HTMLInputElement).value
    ).toBe("");
    expect(JSON.parse(String((fetcher.mock.calls[0]?.[1] as RequestInit).body))).toEqual({
      handle: "some-handle",
      passphrase: "secret words"
    });
  });

  it("fails generically for wrong credentials and keeps them out of the message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("invalid_credentials", 403)));
    mountHandle();
    await enabled(en.handle.delete.submit);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(en.handle.delete.handleLabel), "who");
    await user.type(screen.getByLabelText(en.handle.delete.passphraseLabel), "secret words");
    await user.click(screen.getByRole("checkbox", { name: /I understand the reports stay/ }));
    await user.click(screen.getByRole("button", { name: en.handle.delete.submit }));

    expect(await screen.findByText(en.problems.codes.invalidCredentials)).toBeTruthy();
    expect(document.body.textContent).not.toContain("secret words is");
  });
});
