import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LanguageAnnouncer } from "@/components/shell/language-announcer";
import { LANGUAGE_SWITCH_FLAG, LanguageLink } from "@/components/shell/language-link";
import { PublicShell } from "@/components/shell/shell";
import { setUnsavedDraft } from "@/lib/draft-guard";
import en from "../../messages/en.json";

const guard = en.language.draft;
const links = {
  home: "/en",
  localities: "/en/l",
  report: "/en/report",
  sources: "/en/s",
  trust: "/en/t"
};

beforeEach(() => {
  sessionStorage.clear();
});

afterEach(() => {
  setUnsavedDraft(false);
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function link() {
  return (
    <LanguageLink className="x" guard={guard} href="/ha/projects?q=clinic" lang="ha" language="ha">
      Hausa
    </LanguageLink>
  );
}

describe("language link", () => {
  it("is an ordinary link to the equivalent page and marks the switch when there is no draft", async () => {
    const user = userEvent.setup();
    render(link());
    const anchor = screen.getByRole("link", { name: "Hausa" });

    expect(anchor).toHaveAttribute("href", "/ha/projects?q=clinic");
    expect(anchor).toHaveAttribute("hreflang", "ha");
    expect(anchor).toHaveAttribute("lang", "ha");
    // jsdom cannot navigate; stop the default so the assertion can run.
    anchor.addEventListener("click", (event) => event.preventDefault());
    await user.click(anchor);

    expect(sessionStorage.getItem(LANGUAGE_SWITCH_FLAG)).toBe("ha");
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("warns before discarding an unsaved draft, and staying keeps the page and the focus", async () => {
    const user = userEvent.setup();
    setUnsavedDraft(true);
    render(link());
    const anchor = screen.getByRole("link", { name: "Hausa" });

    await user.click(anchor);

    const dialog = await screen.findByRole("alertdialog", { name: guard.title });
    expect(dialog).toHaveAccessibleDescription(guard.body);
    expect(sessionStorage.getItem(LANGUAGE_SWITCH_FLAG)).toBeNull();

    await user.click(screen.getByRole("button", { name: guard.stay }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(anchor).toHaveFocus();
    expect(sessionStorage.getItem(LANGUAGE_SWITCH_FLAG)).toBeNull();
  });

  it("closes on Escape without switching, and switches only on the explicit confirmation", async () => {
    const user = userEvent.setup();
    const assign = vi.fn();
    vi.stubGlobal("location", { assign });
    setUnsavedDraft(true);
    render(link());

    await user.click(screen.getByRole("link", { name: "Hausa" }));
    await screen.findByRole("alertdialog");
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(assign).not.toHaveBeenCalled();

    await user.click(screen.getByRole("link", { name: "Hausa" }));
    await user.click(await screen.findByRole("button", { name: guard.leave }));
    expect(assign).toHaveBeenCalledExactlyOnceWith("/ha/projects?q=clinic");
    expect(sessionStorage.getItem(LANGUAGE_SWITCH_FLAG)).toBe("ha");
  });
});

describe("language announcer", () => {
  const props = {
    current: "ha",
    language: "en",
    languageName: "Hausa",
    template: en.language.changed
  };

  async function settle() {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 5));
    });
  }

  it("announces the switch once in the language its text is written in, then clears the flag", async () => {
    sessionStorage.setItem(LANGUAGE_SWITCH_FLAG, "ha");
    const { container } = render(<LanguageAnnouncer {...props} />);
    await settle();

    const message = screen.getByText("Language changed to Hausa.");
    expect(message).toHaveAttribute("lang", "en");
    expect(container).toContainElement(message);
    expect(sessionStorage.getItem(LANGUAGE_SWITCH_FLAG)).toBeNull();
  });

  it("stays silent on an ordinary load, or when the flag names a different language", async () => {
    const { container, rerender } = render(<LanguageAnnouncer {...props} />);
    await settle();
    expect(container).toBeEmptyDOMElement();

    sessionStorage.setItem(LANGUAGE_SWITCH_FLAG, "yo");
    rerender(<LanguageAnnouncer {...props} template={`${props.template} `} />);
    await settle();
    expect(container).toBeEmptyDOMElement();
    expect(sessionStorage.getItem(LANGUAGE_SWITCH_FLAG)).toBeNull();
  });

  it("clears the message after a few seconds", async () => {
    vi.useFakeTimers();
    sessionStorage.setItem(LANGUAGE_SWITCH_FLAG, "ha");
    const { container } = render(<LanguageAnnouncer {...props} />);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(container).not.toBeEmptyDOMElement();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(9000);
    });
    expect(container).toBeEmptyDOMElement();
  });
});

describe("shell integration", () => {
  it("renders links through the guard when a language switch is configured, and announces in the status region", async () => {
    sessionStorage.setItem(LANGUAGE_SWITCH_FLAG, "ha");
    render(
      <PublicShell
        currentLocale="ha"
        languageSwitch={{ announce: en.language.changed, announceLanguage: "en", guard }}
        links={links}
        localeRoutes={{ en: "/en", ha: "/ha", ig: "/ig", yo: "/yo" }}
        messages={en.shell.public}
      >
        <p>x</p>
      </PublicShell>
    );
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 5));
    });

    expect(screen.getByRole("link", { name: "English" })).toHaveAttribute("href", "/en");
    const region = document.querySelector("[data-slot=shell-status]");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveTextContent("Language changed to Hausa.");
  });
});
