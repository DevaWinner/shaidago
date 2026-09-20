import { describe, expect, it } from "vitest";

import manifest from "../../app/manifest";

describe("web app manifest", () => {
  const value = manifest();

  it("uses the real product name and the approved canvas colour", () => {
    expect(value.name).toBe("ShaidaGo");
    expect(value.short_name).toBe("ShaidaGo");
    expect(value.theme_color).toBe("#F7F2E8");
    expect(value.background_color).toBe("#F7F2E8");
  });

  it("starts at the root so the locale proxy picks the visitor's language, within one scope", () => {
    expect(value.start_url).toBe("/");
    expect(value.scope).toBe("/");
    expect(value.display).toBe("standalone");
  });

  it("declares the evidence-search icons, including a maskable one, and claims nothing unapproved", () => {
    const icons = value.icons ?? [];

    expect(icons.map((icon) => icon.sizes)).toEqual(expect.arrayContaining(["192x192", "512x512"]));
    expect(icons.some((icon) => icon.purpose === "maskable")).toBe(true);
    expect(icons.every((icon) => icon.src.startsWith("/icons/"))).toBe(true);
    expect(value.screenshots).toBeUndefined();
    expect(value.shortcuts).toBeUndefined();
  });
});
