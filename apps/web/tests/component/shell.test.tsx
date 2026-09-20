import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PublicShell, ReviewerShell } from "@/components/shell/shell";
import { SignOutButton } from "@/components/shell/sign-out-button";
import en from "../../messages/en.json";

const publicShellMessages = en.shell.public;
const reviewerShellMessages = en.shell.reviewer;

const links = {
  home: "/",
  localities: "/localities",
  report: "/report",
  reviewer: "/reviewer/sign-in",
  sources: "/trust#sources",
  track: "/track",
  trust: "/trust"
};

function renderPublic(lowData?: React.ReactNode) {
  return render(
    <PublicShell
      currentLocale="en"
      links={links}
      {...(lowData === undefined ? {} : { lowDataControl: lowData })}
      localeRoutes={{ en: "/" }}
      messages={publicShellMessages}
    >
      <h1>Page</h1>
    </PublicShell>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("public shell", () => {
  it("puts the skip link first and moves focus to main content", async () => {
    const user = userEvent.setup();
    renderPublic();

    await user.tab();
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip).toHaveFocus();
    expect(skip).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(screen.getByRole("main")).toHaveAttribute("tabindex", "-1");
  });

  it("exposes banner, labelled navigation landmarks, main, and a labelled footer", () => {
    renderPublic();

    expect(screen.getByRole("banner")).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Main" })).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Language" })).toBeInTheDocument();
    expect(screen.getByRole("contentinfo", { name: "About ShaidaGo" })).toBeVisible();
    expect(
      within(screen.getByRole("navigation", { name: "Main" })).getAllByRole("link")
    ).toHaveLength(5);
    expect(screen.getByText(/not an emergency service/)).toBeVisible();
  });

  it("marks the current language and shows unreviewed ones as unavailable, never as links", () => {
    renderPublic();
    const locale = screen.getByRole("navigation", { name: "Language" });

    expect(within(locale).getByText("English").closest("[aria-current]")).not.toBeNull();
    expect(within(locale).queryAllByRole("link")).toHaveLength(0);
    for (const name of ["Hausa", "Igbo", "Yorùbá"]) {
      const item = within(locale).getByText(name).closest("[aria-disabled='true']");
      expect(item).toHaveTextContent("not yet reviewed");
      expect(item).toHaveAttribute("lang");
    }
  });

  it("opens the top-right language dropdown without replacing its real links", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <PublicShell
        currentLocale="en"
        links={links}
        localeRoutes={{ en: "/", ha: "/ha" }}
        messages={publicShellMessages}
      >
        <p>x</p>
      </PublicShell>
    );
    const summary = container.querySelector("[data-slot=locale-control] > summary");

    expect(summary).not.toBeNull();
    expect(screen.getByRole("navigation", { name: "Language" })).not.toBeVisible();
    await user.click(summary as HTMLElement);
    expect(screen.getByRole("navigation", { name: "Language" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Hausa" })).toHaveAttribute("href", "/ha");
  });

  it("labels a linked language that has no reviewed copy, outside the link and in English", () => {
    render(
      <PublicShell
        currentLocale="ha"
        links={links}
        localeRoutes={{ en: "/en", ha: "/ha", ig: "/ig", yo: "/yo" }}
        messages={publicShellMessages}
        unreviewedLocales={["ha", "ig", "yo"]}
      >
        <p>x</p>
      </PublicShell>
    );
    const locale = screen.getByRole("navigation", { name: "Language" });

    expect(within(locale).getByRole("link", { name: "English" })).toHaveAttribute("href", "/en");
    expect(within(locale).getByRole("link", { name: "Igbo" })).toHaveAttribute("href", "/ig");
    expect(within(locale).getByRole("link", { name: "Igbo" })).toHaveAttribute("lang", "ig");
    expect(within(locale).getAllByText("(not yet reviewed)")).toHaveLength(3);
    for (const note of within(locale).getAllByText("(not yet reviewed)")) {
      expect(note).toHaveAttribute("lang", "en");
      expect(note.closest("a")).toBeNull();
    }
    expect(within(locale).queryByRole("link", { name: "Hausa" })).toBeNull();
    expect(within(locale).getByText("Hausa").closest("[aria-current]")).not.toBeNull();
  });

  it("links a language once its route exists", () => {
    render(
      <PublicShell
        currentLocale="en"
        links={links}
        localeRoutes={{ en: "/", ha: "/ha" }}
        messages={publicShellMessages}
      >
        <p>x</p>
      </PublicShell>
    );
    expect(screen.getByRole("link", { name: "Hausa" })).toHaveAttribute("href", "/ha");
    expect(screen.getByRole("link", { name: "Hausa" })).toHaveAttribute("hreflang", "ha");
  });

  it("renders an empty polite status region and no low-data control unless one is supplied", () => {
    const { container } = renderPublic();
    const region = container.querySelector("[data-slot=shell-status]");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toBeEmptyDOMElement();
    expect(screen.queryByText(/low-data/i)).toBeNull();
  });

  it("keeps every navigation destination as a plain anchor", () => {
    renderPublic();
    const navigation = screen.getByRole("navigation", { name: "Main" });
    expect(
      within(navigation).getByRole("link", { name: "Track or access reports" })
    ).toHaveAttribute("href", "/track");
    expect(within(navigation).getByRole("link", { name: "Reviewer sign-in" })).toHaveAttribute(
      "href",
      "/reviewer/sign-in"
    );
  });

  it("marks the active destination in words and with aria-current", () => {
    render(
      <PublicShell
        active="localities"
        currentLocale="en"
        links={links}
        localeRoutes={{ en: "/" }}
        messages={publicShellMessages}
      >
        <h1>Page</h1>
      </PublicShell>
    );

    expect(screen.getByRole("link", { name: "Project records", current: "page" })).toBeVisible();
  });
});

describe("reviewer shell", () => {
  it("uses plain anchors so no private route is prefetched, and hosts the session control", () => {
    const { container } = render(
      <ReviewerShell
        homeHref="/reviewer"
        messages={reviewerShellMessages}
        queueHref="/reviewer/reports"
        sessionControl={<button type="button">Sign out</button>}
      >
        <h1>Queue</h1>
      </ReviewerShell>
    );

    expect(screen.getByRole("link", { name: "Report queue" })).toHaveAttribute(
      "href",
      "/reviewer/reports"
    );
    expect(container.querySelectorAll("a[data-prefetch], link[rel='prefetch']")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Sign out" })).toBeVisible();
    expect(screen.getByText("Reviewer", { selector: "[data-slot=shell-area]" })).toBeVisible();
  });
});

describe("sign-out button", () => {
  const props = {
    failedMessage: "Sign-out could not be confirmed. Try again.",
    label: "Sign out",
    pendingLabel: "Signing out",
    signedOutHref: "/reviewer/sign-in"
  };

  it("calls the same-origin handler with no token and no body, then leaves", async () => {
    const user = userEvent.setup();
    const assign = vi.fn();
    vi.stubGlobal("location", { assign });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    render(<SignOutButton {...props} />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => expect(assign).toHaveBeenCalledWith("/reviewer/sign-in"));
    expect(fetchSpy).toHaveBeenCalledWith("/api/reviewer/session", {
      method: "DELETE",
      credentials: "same-origin"
    });
    vi.unstubAllGlobals();
  });

  it("states a failure instead of implying the session ended", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 503 }));
    render(<SignOutButton {...props} />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("could not be confirmed");
  });

  it("reports a network failure and ignores a second click while pending", async () => {
    const user = userEvent.setup();
    let reject: (reason: Error) => void = () => undefined;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(
      () =>
        new Promise((_resolve, rejectFetch) => {
          reject = rejectFetch;
        })
    );
    render(<SignOutButton {...props} />);

    await user.click(screen.getByRole("button", { name: "Sign out" }));
    await user.click(screen.getByRole("button", { name: "Signing out" }));
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    reject(new Error("offline"));
    expect(await screen.findByRole("alert")).toBeVisible();
  });
});
