import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { readFileSync } from "node:fs";
import { join } from "node:path";

// Playwright's own JSX transform cannot server-render project components, so the vitest unit
// project renders them to this file first (`pnpm run a11y` does both in order).
const SHEET_PATH = join(import.meta.dirname, "..", ".generated", "primitives-sheet.html");

function primitiveSheetMarkup(): string {
  return readFileSync(SHEET_PATH, "utf8");
}

const CONTROL_SELECTOR = "[data-slot=button], [data-slot=input], [data-slot=choice], summary";

async function loadSheet(page: Page): Promise<void> {
  await page.goto("/");
  await page.evaluate((markup) => {
    document.body.innerHTML = markup;
  }, primitiveSheetMarkup());
}

async function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

test("the primitive sheet has no automated axe violations with the real stylesheet", async ({
  page
}) => {
  await loadSheet(page);

  const results = await new AxeBuilder({ page }).analyze();

  expect(results.violations).toEqual([]);
});

test("every control is at least 44 by 44 CSS pixels", async ({ page }) => {
  await loadSheet(page);

  const undersized = await page.$$eval(CONTROL_SELECTOR, (elements) =>
    elements
      .map((element) => ({
        name: element.className || element.tagName,
        box: element.getBoundingClientRect()
      }))
      .filter(({ box }) => box.height > 0 && (box.height < 43.5 || box.width < 43.5))
      .map(({ name, box }) => `${name}: ${Math.round(box.width)}x${Math.round(box.height)}`)
  );

  expect(undersized).toEqual([]);
});

test("content reflows at 320 CSS pixels and at 200% text size without horizontal scrolling", async ({
  page
}) => {
  await loadSheet(page);

  await page.setViewportSize({ width: 320, height: 800 });
  expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);

  await page.setViewportSize({ width: 640, height: 800 });
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "200%";
  });
  expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);

  const clipped = await page.$$eval(CONTROL_SELECTOR, (elements) =>
    elements
      .filter((element) => element.scrollWidth > element.clientWidth + 1)
      .map((e) => e.className)
  );
  expect(clipped).toEqual([]);
});

test("controls use project tokens, not native browser styling", async ({ page }) => {
  await loadSheet(page);

  const styles = await page.evaluate(() => {
    const read = (selector: string) => {
      const element = document.querySelector(selector);

      if (element === null) {
        throw new Error(`missing ${selector}`);
      }

      const style = getComputedStyle(element);

      return {
        font: style.fontFamily,
        radius: style.borderTopLeftRadius,
        background: style.backgroundColor,
        color: style.color
      };
    };

    return {
      body: getComputedStyle(document.body).fontFamily,
      primary: read("[data-slot=button][data-variant=primary]"),
      secondary: read("[data-slot=button][data-variant=secondary]"),
      input: read("#f2"),
      readOnly: read("#f3")
    };
  });

  expect(styles.primary.font).toBe(styles.body);
  expect(styles.input.font).toBe(styles.body);
  expect(styles.primary.radius).toBe("4px");
  expect(styles.primary.background).toBe("rgb(0, 110, 101)");
  expect(styles.primary.color).toBe("rgb(255, 255, 255)");
  expect(styles.secondary.background).toBe("rgb(255, 252, 246)");
  expect(styles.readOnly.background).toBe("rgb(238, 232, 220)");
});

test("keyboard focus is a visible three-pixel ring, and stronger under forced colours", async ({
  page
}) => {
  await loadSheet(page);
  await page.keyboard.press("Tab");

  const ring = await page.evaluate(() => {
    const style = getComputedStyle(document.activeElement as Element);

    return { style: style.outlineStyle, width: style.outlineWidth };
  });
  expect(ring).toEqual({ style: "solid", width: "3px" });

  await page.emulateMedia({ forcedColors: "active" });
  const forced = await page.evaluate(() => {
    const focused = getComputedStyle(document.activeElement as Element);
    const button = getComputedStyle(
      document.querySelector("[data-slot=button][data-variant=primary]") as Element
    );

    return {
      outline: focused.outlineStyle,
      outlineWidth: focused.outlineWidth,
      border: button.borderTopWidth
    };
  });
  expect(forced.outline).toBe("solid");
  expect(Number.parseFloat(forced.outlineWidth)).toBeGreaterThanOrEqual(3);
  expect(Number.parseFloat(forced.border)).toBeGreaterThanOrEqual(2);
});

test("reduced motion leaves no transition or animation on primitives", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await loadSheet(page);

  const motion = await page.$$eval(
    "[data-slot=button], [data-slot=skeleton], [data-slot=input]",
    (elements) =>
      elements.map((element) => {
        const style = getComputedStyle(element);

        return `${style.animationName}|${style.transitionDuration}`;
      })
  );

  expect(new Set(motion)).toEqual(new Set(["none|0s"]));
});

test("the citation stitch works with plain links, moves focus, and marks both ends", async ({
  page
}) => {
  await loadSheet(page);

  await page.getByRole("link", { name: "Source 1" }).click();

  expect(await page.evaluate(() => location.hash)).toBe("#citation-c1");
  const target = await page.evaluate(() => {
    const entry = document.getElementById("citation-c1") as HTMLElement;
    const style = getComputedStyle(entry);

    return {
      focused: document.activeElement === entry || entry.matches(":target"),
      outline: style.outlineStyle,
      width: style.outlineWidth
    };
  });
  expect(target).toEqual({ focused: true, outline: "solid", width: "3px" });
});
