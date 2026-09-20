import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const stylesheetPath = fileURLToPath(new URL("../../app/globals.css", import.meta.url));

const contrastPairs = [
  ["--color-text", "--color-canvas"],
  ["--color-text", "--color-surface"],
  ["--color-muted", "--color-canvas"],
  ["--color-muted", "--color-surface"],
  ["--color-accent", "--color-canvas"],
  ["--color-warning", "--color-canvas"],
  ["--color-danger", "--color-surface"],
  ["--color-information", "--color-canvas"],
  ["--color-on-accent", "--color-accent"],
  ["--color-on-danger", "--color-danger"],
  ["--color-on-information", "--color-information"],
  ["--state-selected-text", "--state-selected-background"],
  ["--state-read-only-text", "--state-read-only-background"]
] as const;

function parseHexTokens(stylesheet: string): Map<string, string> {
  return new Map(
    [...stylesheet.matchAll(/^\s*(--[\w-]+):\s*(#[\da-f]{6});$/gim)].map((match) => [
      match[1] ?? "",
      match[2] ?? ""
    ])
  );
}

function firstRootBlock(stylesheet: string): string {
  const rootBlock = stylesheet.match(/^:root \{(?<declarations>[\s\S]*?)^\}$/m)?.[0];

  if (rootBlock === undefined) {
    throw new Error("Expected the Field Ledger root token block.");
  }

  return rootBlock;
}

function relativeLuminance(hex: string): number {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)
    ?.map((channel) => Number.parseInt(channel, 16) / 255);

  if (channels?.length !== 3) {
    throw new Error(`Expected a six-digit hexadecimal colour, received ${hex}.`);
  }

  const red = channels[0];
  const green = channels[1];
  const blue = channels[2];

  if (red === undefined || green === undefined || blue === undefined) {
    throw new Error(`Expected three colour channels, received ${hex}.`);
  }

  return [red, green, blue]
    .map((channel) => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4))
    .reduce((total, channel, index) => {
      const coefficients = [0.2126, 0.7152, 0.0722] as const;
      return total + channel * coefficients[index]!;
    }, 0);
}

function contrastRatio(first: string, second: string): number {
  const [lighter, darker] = [relativeLuminance(first), relativeLuminance(second)].sort(
    (left, right) => right - left
  );

  return (lighter! + 0.05) / (darker! + 0.05);
}

describe("Field Ledger design tokens", async () => {
  const stylesheet = await readFile(stylesheetPath, "utf8");
  const tokens = parseHexTokens(firstRootBlock(stylesheet));

  it("defines every semantic colour role and named evidence state", () => {
    expect(Object.fromEntries(tokens)).toEqual(
      expect.objectContaining({
        "--color-canvas": "#f7f2e8",
        "--color-surface": "#fffcf6",
        "--color-text": "#172323",
        "--color-muted": "#526260",
        "--color-accent": "#006e65",
        "--color-danger": "#a7383b",
        "--color-success": "#006e65",
        "--color-warning": "#9d5c16",
        "--color-information": "#005fcc"
      })
    );
    expect(stylesheet).toContain("--status-reviewed: var(--color-success);");
    expect(stylesheet).toContain("--status-under-review: var(--color-warning);");
    expect(stylesheet).toContain("--status-limited-evidence: var(--color-information);");
    expect(stylesheet).toContain("--status-unavailable: var(--color-muted);");
  });

  it.each(contrastPairs)("keeps %s legible on %s", (foregroundToken, backgroundToken) => {
    const foreground = tokens.get(foregroundToken);
    const background = tokens.get(backgroundToken);

    expect(foreground).toBeDefined();
    expect(background).toBeDefined();
    expect(contrastRatio(foreground!, background!)).toBeGreaterThanOrEqual(4.5);
  });

  it("preserves focus, contrast, forced-colours, and motion overrides", () => {
    expect(stylesheet).toContain("inline-size: min(calc(100% - (var(--layout-gutter) * 2))");
    expect(stylesheet).toContain("font-size: var(--font-size-display);");
    expect(stylesheet).toContain(":focus-visible");
    expect(stylesheet).toContain("@media (prefers-contrast: more)");
    expect(stylesheet).toContain("@media (forced-colors: active)");
    expect(stylesheet).toContain("CanvasText");
    expect(stylesheet).toContain("HighlightText");
    expect(stylesheet).toContain("@media (prefers-reduced-motion: reduce)");
    expect(stylesheet).toContain("transition-duration: var(--motion-none) !important;");
  });
});
