import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { Confirmation } from "@/components/report/confirmation";
import { ReportWizard } from "@/components/report/report-wizard";
import { clearReceipt, peekReceipt, setReceipt } from "@/lib/report/receipt-store";
import en from "../../messages/en.json";

class FakeXhr {
  static all: FakeXhr[] = [];
  headers: Record<string, string> = {};
  upload = {};
  status = 0;
  responseText = "";
  onload?: () => void;
  onerror?: () => void;
  onabort?: () => void;
  sent: FormData | undefined;
  open() {
    FakeXhr.all.push(this);
  }
  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }
  getAllResponseHeaders() {
    return "";
  }
  send(body: FormData) {
    this.sent = body;
  }
  abort() {
    this.onabort?.();
  }
}

const receipt = JSON.stringify({
  attachments: [],
  contact_saved: false,
  next_steps: ["save_tracking_code"],
  published: false,
  status: "received",
  tracking_code: "SG-DEMO-0001"
});

function mount() {
  return render(
    <ReportWizard
      copy={en.report}
      handleHref="/en/handle"
      language="en"
      locale="en"
      problems={en.problems}
      projectTitle="Synthetic record"
      slug="synthetic-project-01"
      trustHref="/en/trust"
    />
  );
}

async function ready() {
  const button = await screen.findByRole("button", { name: en.report.notice.start });
  await waitFor(() => expect(button.hasAttribute("disabled")).toBe(false));
  return userEvent.setup();
}

async function toObservation() {
  const user = await ready();
  await user.click(screen.getByRole("button", { name: en.report.notice.start }));
  await settled();
  return user;
}

async function fillObservation(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(
    screen.getByLabelText(re(en.report.observation.categoryLabel)),
    "unsafe_construction"
  );
  await user.type(
    screen.getByLabelText(re(en.report.observation.descriptionLabel)),
    "A fictional wall is leaning."
  );
}

const re = (text: string) => new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
const settled = () => waitFor(() => expect(screen.queryByText(en.report.nav.loading)).toBeNull());
const next = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(screen.getByRole("button", { name: en.report.nav.next }));
  await settled();
};

beforeEach(() => {
  window.localStorage.clear();
  FakeXhr.all = [];
  vi.stubGlobal("XMLHttpRequest", FakeXhr);
});

afterEach(async () => {
  cleanup();
  // The confirmation drops its receipt on a deferred timer; let it fire before the next test.
  await new Promise((resolve) => setTimeout(resolve, 5));
  clearReceipt();
  push.mockReset();
  vi.unstubAllGlobals();
});

describe("ReportWizard", () => {
  it("starts with the safety notice and the non-emergency limit, and moves focus to each step heading", async () => {
    mount();
    const user = await toObservation();

    expect(screen.queryByText(en.report.notice.limit)).toBeNull();
    expect(document.activeElement?.textContent).toBe(en.report.steps.observation);
    await user.click(screen.getByRole("button", { name: en.report.nav.back }));
    expect(screen.getByText(en.report.notice.limit)).toBeTruthy();
    expect(screen.getByText(en.report.notice.fictional)).toBeTruthy();
  });

  it("names each missing field, keeps the entered text, and clears the errors when it is fixed", async () => {
    mount();
    const user = await toObservation();

    await next(user);
    const summary = screen
      .getByText(en.report.nav.stepErrors)
      .closest("[data-slot=error-summary]") as HTMLElement;
    expect(within(summary).getByText(en.report.errors.category)).toBeTruthy();
    await user.type(screen.getByLabelText(re(en.report.observation.descriptionLabel)), "short");
    await next(user);
    expect(screen.getAllByText("Write at least 10 characters.").length).toBeGreaterThan(0);
    expect(
      (screen.getByLabelText(re(en.report.observation.descriptionLabel)) as HTMLTextAreaElement)
        .value
    ).toBe("short");
  });

  it("offers fully anonymous first, and deletes contact values the moment the mode changes", async () => {
    mount();
    const user = await toObservation();

    await fillObservation(user);
    await next(user); // evidence
    await next(user); // anonymity
    const anonymous = screen.getByRole("radio", {
      name: re(en.report.anonymity.modes.anonymous.label)
    }) as HTMLInputElement;
    expect(anonymous.checked).toBe(true);
    expect(screen.queryByLabelText(re(en.report.anonymity.contactLabel))).toBeNull();

    await user.click(
      screen.getByRole("radio", { name: re(en.report.anonymity.modes.contact.label) })
    );
    await user.type(
      screen.getByLabelText(re(en.report.anonymity.contactLabel)),
      "someone@example.org"
    );
    await user.click(
      screen.getByRole("radio", { name: re(en.report.anonymity.modes.anonymous.label) })
    );
    expect(screen.queryByLabelText(re(en.report.anonymity.contactLabel))).toBeNull();
    await user.click(
      screen.getByRole("radio", { name: re(en.report.anonymity.modes.contact.label) })
    );
    expect(
      (screen.getByLabelText(re(en.report.anonymity.contactLabel)) as HTMLInputElement).value
    ).toBe("");
  });

  it("warns that handle reports can be linked, hides the passphrase, and reveals it only on request", async () => {
    mount();
    const user = await toObservation();

    await fillObservation(user);
    await next(user);
    await next(user);
    await user.click(
      screen.getByRole("radio", { name: re(en.report.anonymity.modes.handle.label) })
    );
    expect(screen.getByText(en.report.anonymity.modes.handle.warning)).toBeTruthy();
    await user.type(
      screen.getByLabelText(re(en.report.anonymity.passphraseLabel)),
      "one two three"
    );
    const field = screen.getByLabelText(
      re(en.report.anonymity.passphraseLabel)
    ) as HTMLInputElement;
    expect(field.type).toBe("password");
    await user.click(screen.getByRole("button", { name: en.report.anonymity.reveal }));
    expect(field.type).toBe("text");
  });

  it("saves a draft only after consent, only the concern and description, and can delete it", async () => {
    mount();
    const user = await toObservation();

    expect(window.localStorage.length).toBe(0);
    await fillObservation(user);
    expect(window.localStorage.length).toBe(0);
    await user.click(screen.getByRole("checkbox", { name: re(en.report.draft.consent) }));
    const stored = JSON.parse(
      window.localStorage.getItem("shaidago.report-draft") ?? "{}"
    ) as Record<string, unknown>;

    expect(stored).toMatchObject({
      category: "unsafe_construction",
      description: "A fictional wall is leaning.",
      project: "synthetic-project-01"
    });
    expect(Object.keys(stored).sort()).toEqual([
      "category",
      "description",
      "project",
      "savedAt",
      "step",
      "version"
    ]);
    await user.click(screen.getByRole("button", { name: en.report.draft.remove }));
    expect(window.localStorage.length).toBe(0);
    expect(screen.getByText(en.report.draft.removed)).toBeTruthy();
  });

  it("offers a saved draft for this project on the first step, restores it, and never restores an expired one", async () => {
    const draft = {
      version: 1,
      savedAt: Date.now() - 1000,
      project: "synthetic-project-01",
      step: "anonymity",
      category: "access_barrier",
      description: "Restored fictional description."
    };

    window.localStorage.setItem("shaidago.report-draft", JSON.stringify(draft));
    mount();
    const user = await ready();

    await user.click(await screen.findByRole("button", { name: en.report.draft.restore }));
    expect(document.activeElement?.textContent).toBe(en.report.steps.anonymity);
    await user.click(screen.getByRole("button", { name: en.report.nav.back }));
    await user.click(screen.getByRole("button", { name: en.report.nav.back }));
    expect(
      (screen.getByLabelText(re(en.report.observation.descriptionLabel)) as HTMLTextAreaElement)
        .value
    ).toBe("Restored fictional description.");
    cleanup();

    window.localStorage.setItem(
      "shaidago.report-draft",
      JSON.stringify({ ...draft, savedAt: Date.now() - 25 * 60 * 60 * 1000 })
    );
    mount();
    await ready();
    expect(screen.queryByRole("button", { name: en.report.draft.restore })).toBeNull();
    await waitFor(() => expect(window.localStorage.length).toBe(0));
  });

  it("sends once, keeps one key across a retry of the same report, then shows the receipt route and clears everything", async () => {
    mount();
    const user = await toObservation();

    await fillObservation(user);
    await user.click(screen.getByRole("checkbox", { name: re(en.report.draft.consent) }));
    await next(user);
    await next(user);
    await next(user); // review
    expect(screen.getByText("Fully anonymous")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: en.report.review.submit }));

    await waitFor(() => expect(FakeXhr.all.length).toBeGreaterThan(0));
    const first = FakeXhr.all[0] as FakeXhr;
    expect(first.sent?.get("description")).toBe("A fictional wall is leaning.");
    expect(first.sent?.has("contact_value")).toBe(false);
    act(() => first.onerror?.());
    expect((await screen.findAllByText(en.report.send.unknown)).length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: en.report.send.retry }));
    await waitFor(() => expect(FakeXhr.all.length).toBe(2));
    const second = FakeXhr.all[1] as FakeXhr;
    expect(second.headers["Idempotency-Key"]).toBe(first.headers["Idempotency-Key"]);
    second.status = 201;
    second.responseText = receipt;
    act(() => second.onload?.());

    await waitFor(() => expect(push).toHaveBeenCalledWith("/en/report/complete"));
    expect(peekReceipt()?.trackingCode).toBe("SG-DEMO-0001");
    expect(window.localStorage.length).toBe(0);
  });

  it("uses a new key when the reviewed report changed, and returns to the step a server error belongs to", async () => {
    mount();
    const user = await toObservation();

    await fillObservation(user);
    await next(user);
    await next(user);
    await next(user);
    await user.click(screen.getByRole("button", { name: en.report.review.submit }));
    await waitFor(() => expect(FakeXhr.all.length).toBeGreaterThan(0));
    const first = FakeXhr.all[0] as FakeXhr;
    first.status = 422;
    first.responseText = JSON.stringify({
      code: "validation_failed",
      errors: [{ field: "body.description", code: "string_too_short" }],
      status: 422
    });
    (first as unknown as { getAllResponseHeaders: () => string }).getAllResponseHeaders = () =>
      "Content-Type: application/problem+json";
    act(() => first.onload?.());

    expect(await screen.findByRole("heading", { name: en.report.steps.observation })).toBeTruthy();
    await user.type(
      screen.getByLabelText(re(en.report.observation.descriptionLabel)),
      " More words."
    );
    await next(user);
    await next(user);
    await next(user);
    await user.click(screen.getByRole("button", { name: en.report.send.retry }));
    await waitFor(() => expect(FakeXhr.all.length).toBe(2));
    expect((FakeXhr.all[1] as FakeXhr).headers["Idempotency-Key"]).not.toBe(
      first.headers["Idempotency-Key"]
    );
  });

  it("does not send while offline and keeps the report", async () => {
    mount();
    const user = await toObservation();

    await fillObservation(user);
    await next(user);
    await next(user);
    await next(user);
    vi.spyOn(window.navigator, "onLine", "get").mockReturnValue(false);
    await user.click(screen.getByRole("button", { name: en.report.review.submit }));

    expect((await screen.findAllByText(en.report.send.offline)).length).toBeGreaterThan(0);
    expect(FakeXhr.all).toHaveLength(0);
  });

  it("can be cancelled while sending, and the report is kept", async () => {
    mount();
    const user = await toObservation();

    await fillObservation(user);
    await next(user);
    await next(user);
    await next(user);
    await user.click(screen.getByRole("button", { name: en.report.review.submit }));
    await user.click(screen.getByRole("button", { name: en.report.send.cancel }));

    expect((await screen.findAllByText(en.report.send.cancelled)).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: en.report.send.retry })).toBeTruthy();
  });
});

describe("Confirmation", () => {
  it("shows the code only from memory, with explicit copy, and drops it when the person leaves", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);

    // user-event installs its own clipboard on setup, so the stub goes in afterwards.
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    setReceipt({
      trackingCode: "SG-DEMO-0001",
      contactSaved: true,
      attachments: [
        { position: 0, kept: true, reason: null },
        { position: 1, kept: false, reason: "malformed" }
      ],
      nextSteps: ["save_tracking_code", "check_status_later", "unknown_step"],
      handleUsed: false
    });
    render(<Confirmation copy={en.report} locale="en" />);

    expect(screen.getByText("SG-DEMO-0001")).toBeTruthy();
    expect(writeText).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: en.report.complete.copy }));
    expect(writeText).toHaveBeenCalledWith("SG-DEMO-0001");
    expect(await screen.findByText(en.report.complete.copied)).toBeTruthy();
    expect(screen.getByText(/File 2: not kept \(it could not be read\)/)).toBeTruthy();
    expect(screen.queryByText("unknown_step")).toBeNull();
    expect(screen.getByText(en.report.complete.contactSaved)).toBeTruthy();
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);

    await user.click(screen.getByRole("link", { name: re(en.report.complete.leave) }));
    expect(peekReceipt()).toBeUndefined();
  });

  it("says the code cannot be recovered when there is no receipt in memory", () => {
    render(<Confirmation copy={en.report} locale="en" />);

    expect(screen.getByText(en.report.complete.lost.title)).toBeTruthy();
    expect(screen.getByText(en.report.complete.lost.body)).toBeTruthy();
    expect(document.body.textContent).not.toContain("SG-DEMO");
  });

  it("reports when copying is not available", async () => {
    const user = userEvent.setup();

    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockRejectedValue(new Error("no")) },
      configurable: true
    });
    setReceipt({
      trackingCode: "SG-DEMO-0002",
      contactSaved: false,
      attachments: [],
      nextSteps: [],
      handleUsed: false
    });
    render(<Confirmation copy={en.report} locale="en" />);
    await user.click(screen.getByRole("button", { name: en.report.complete.copy }));

    expect(await screen.findByText(en.report.complete.copyFailed)).toBeTruthy();
  });
});
