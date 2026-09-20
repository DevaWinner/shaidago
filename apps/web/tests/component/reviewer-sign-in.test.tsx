import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SignInForm } from "@/components/reviewer/sign-in-form";
import en from "../../messages/en.json";

const problem = (code: string, status: number, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify({ code, status }), {
    status,
    headers: { "Content-Type": "application/problem+json", ...headers }
  });

const assign = vi.fn();

function mount() {
  Object.defineProperty(window, "location", {
    configurable: true,
    value: { ...window.location, assign }
  });

  return render(
    <SignInForm
      copy={en.reviewer.signIn}
      problems={en.problems}
      required={en.reviewer.signIn.required}
      target="/en/reviewer/reports"
    />
  );
}

async function ready() {
  const button = await screen.findByRole("button", { name: en.reviewer.signIn.submit });
  await waitFor(() => expect(button.getAttribute("aria-disabled")).toBe("false"));

  return button;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
  assign.mockReset();
  window.localStorage.clear();
  window.sessionStorage.clear();
});

describe("SignInForm", () => {
  it("labels both fields for a password manager and states what is missing without sending", async () => {
    const fetcher = vi.fn();

    vi.stubGlobal("fetch", fetcher);
    mount();
    const submit = await ready();

    expect(
      screen.getByLabelText(new RegExp(en.reviewer.signIn.identifier)).getAttribute("autocomplete")
    ).toBe("username");
    expect(
      screen.getByLabelText(new RegExp(en.reviewer.signIn.password)).getAttribute("autocomplete")
    ).toBe("current-password");
    await userEvent.setup().click(submit);

    expect(await screen.findByText(en.reviewer.signIn.identifierRequired)).toBeTruthy();
    expect(screen.getByText(en.reviewer.signIn.passwordRequired)).toBeTruthy();
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("posts JSON to the same-origin handler, empties the password, and goes only to the given target", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ reviewer: { role: "reviewer" } }), { status: 201 })
      );

    vi.stubGlobal("fetch", fetcher);
    mount();
    const user = userEvent.setup();

    await ready();
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.identifier)), " r1 ");
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.password)), "secret-value");
    await user.click(screen.getByRole("button", { name: en.reviewer.signIn.submit }));

    await waitFor(() => expect(assign).toHaveBeenCalledWith("/en/reviewer/reports"));
    const [url, init] = fetcher.mock.calls[0] as [string, RequestInit];

    expect(url).toBe("/api/reviewer/session");
    expect(JSON.parse(String(init.body))).toEqual({ identifier: "r1", password: "secret-value" });
    expect(init.credentials).toBe("same-origin");
    expect(
      (screen.getByLabelText(new RegExp(en.reviewer.signIn.password)) as HTMLInputElement).value
    ).toBe("");
    expect(JSON.stringify({ ...window.localStorage, ...window.sessionStorage })).not.toContain(
      "secret-value"
    );
  });

  it("shows one generic message for a rejected sign-in and keeps the identifier but not the password", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(problem("invalid_credentials", 401)));
    mount();
    const user = userEvent.setup();

    await ready();
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.identifier)), "r1");
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.password)), "wrong");
    await user.click(screen.getByRole("button", { name: en.reviewer.signIn.submit }));

    const alert = await screen.findByRole("alert");

    expect(alert.textContent).toContain(en.problems.codes.invalidCredentials);
    expect(alert.textContent).not.toMatch(
      /password (is|was) (wrong|incorrect)|unknown (user|identifier)/i
    );
    expect(
      (screen.getByLabelText(new RegExp(en.reviewer.signIn.password)) as HTMLInputElement).value
    ).toBe("");
    expect(assign).not.toHaveBeenCalled();
  });

  it("displays the back-off after a rate limit and holds the button until it ends", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(problem("rate_limited", 429, { "Retry-After": "2" }))
    );
    mount();
    const user = userEvent.setup();

    await ready();
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.identifier)), "r1");
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.password)), "x");
    await user.click(screen.getByRole("button", { name: en.reviewer.signIn.submit }));

    expect((await screen.findByText(/You can try again in \d seconds\./)).textContent).toMatch(
      /[12] seconds/
    );
    expect(
      screen.getByRole("button", { name: en.reviewer.signIn.submit }).getAttribute("aria-disabled")
    ).toBe("true");
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 2200));
    });
    await waitFor(() =>
      expect(
        screen
          .getByRole("button", { name: en.reviewer.signIn.submit })
          .getAttribute("aria-disabled")
      ).toBe("false")
    );
  });

  it("says the service is unreachable when the connection fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    mount();
    const user = userEvent.setup();

    await ready();
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.identifier)), "r1");
    await user.type(screen.getByLabelText(new RegExp(en.reviewer.signIn.password)), "x");
    await user.click(screen.getByRole("button", { name: en.reviewer.signIn.submit }));

    expect((await screen.findByRole("alert")).textContent).toContain(en.problems.codes.network);
  });
});
