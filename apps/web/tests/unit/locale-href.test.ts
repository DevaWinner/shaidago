import { afterEach, describe, expect, it } from "vitest";

import { localeHref } from "@/i18n/locale-href";
import { hasUnsavedDraft, setUnsavedDraft, subscribeToDraft } from "@/lib/draft-guard";

describe("localeHref", () => {
  it("keeps the route and shareable filters, and starts again from the first page", () => {
    const href = localeHref("ha", {
      segments: ["projects"],
      keep: ["locality", "category", "q", "cursor"],
      search: {
        locality: "amac",
        category: "health",
        q: "clinic",
        cursor: "opaque-cursor",
        other: "x"
      }
    });

    expect(href).toBe("/ha/projects?locality=amac&category=health&q=clinic");
    expect(href).not.toContain("cursor");
    expect(href).not.toContain("other");
  });

  it("keeps repeated filters, skips empty ones, and encodes every value and segment", () => {
    expect(
      localeHref("yo", {
        segments: ["projects", "a b/c"],
        keep: ["status", "q"],
        search: { status: ["planned", "in_progress"], q: "" }
      })
    ).toBe("/yo/projects/a%20b%2Fc?status=planned&status=in_progress");
    expect(localeHref("ig", { keep: ["q"], search: { q: "a&b=c" } })).toBe("/ig?q=a%26b%3Dc");
  });

  it("builds only from parsed route state, so it cannot become an open redirect or carry other data", () => {
    for (const hostile of [
      "//evil.example",
      "https://evil.example",
      "/\\evil.example",
      "../../etc"
    ]) {
      const href = localeHref("en", { segments: [hostile], keep: ["q"], search: { q: hostile } });

      expect(href.startsWith("/en/"), hostile).toBe(true);
      expect(href, hostile).not.toMatch(/^\/en\/\/|^\/\//);
      expect(new URL(href, "https://shaidago.example").origin, hostile).toBe(
        "https://shaidago.example"
      );
    }
    // Drafts, tracking codes, and contacts are not route state, so they can never appear.
    expect(
      localeHref("en", { segments: ["report"], search: { draft: "text", code: "SG-1" } })
    ).toBe("/en/report");
  });

  it("gives a bare locale route when there is no path or filter", () => {
    expect(localeHref("en")).toBe("/en");
    expect(localeHref("ha", { segments: [] })).toBe("/ha");
  });
});

describe("draft guard", () => {
  afterEach(() => {
    setUnsavedDraft(false);
  });

  it("tracks the flag in memory only and notifies listeners once per change", () => {
    let calls = 0;
    const stop = subscribeToDraft(() => {
      calls += 1;
    });

    expect(hasUnsavedDraft()).toBe(false);
    setUnsavedDraft(true);
    setUnsavedDraft(true);
    expect(hasUnsavedDraft()).toBe(true);
    setUnsavedDraft(false);
    expect(calls).toBe(2);
    stop();
    setUnsavedDraft(true);
    expect(calls).toBe(2);
  });
});
