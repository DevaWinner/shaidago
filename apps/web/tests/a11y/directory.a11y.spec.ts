import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["en", "ha", "ig", "yo"] as const;
const STATES: Record<string, string> = {
  results: "projects",
  filtered: "projects?category=health&locality=amac",
  "no matches": "projects?q=zzzz-nothing-matches",
  unavailable: "projects?q=__unavailable",
  "invalid cursor": "projects?cursor=stale-cursor-value"
};

for (const locale of LOCALES) {
  for (const [name, path] of Object.entries(STATES)) {
    test(`${locale} directory (${name}): no automated axe violations`, async ({ page }) => {
      await page.goto(`/${locale}/${path}`);

      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    });
  }
}

async function overflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

for (const locale of LOCALES) {
  test(`${locale} directory: reflows at 320 px and 200% text, and targets are at least 44 px`, async ({
    page
  }) => {
    await page.goto(`/${locale}/projects?category=health`);

    await page.setViewportSize({ width: 320, height: 800 });
    expect(await overflow(page)).toBeLessThanOrEqual(0);
    await page.setViewportSize({ width: 640, height: 800 });
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "200%";
    });
    expect(await overflow(page)).toBeLessThanOrEqual(0);
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "";
    });

    const small = await page.$$eval(
      "[data-slot=button], [data-slot=input], [data-slot=filter-pills] a, [data-slot=pagination] a, nav a",
      (elements) =>
        elements
          .map((element) => ({
            name: element.textContent?.trim() ?? "",
            box: element.getBoundingClientRect()
          }))
          .filter(({ box }) => box.height > 0 && box.height < 43.5)
          .map(({ name, box }) => `${name}: ${Math.round(box.height)}px`)
    );
    expect(small).toEqual([]);
  });
}

test("results are a labelled region with one live count and named links", async ({ page }) => {
  await page.goto("/en/projects");

  await expect(page.getByRole("region", { name: "Results" })).toBeVisible();
  await expect(
    page.locator("[role=status][aria-live=polite]").filter({ hasText: "Showing 12" })
  ).toHaveCount(1);
  // Every card link is named by its own project title, not a repeated "View record".
  const names = await page.locator("[data-slot=project-card] h2 a").allInnerTexts();
  expect(new Set(names).size).toBe(names.length);
  await expect(page.getByRole("link", { name: /^(view|read more|click here)/i })).toHaveCount(0);
});

test("reduced motion leaves no animation or transition on the directory", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/en/projects");

  const motion = await page.$$eval("main *", (elements) => [
    ...new Set(
      elements.map(
        (element) =>
          `${getComputedStyle(element).animationName}|${getComputedStyle(element).transitionDuration}`
      )
    )
  ]);
  expect(motion).toEqual(["none|0s"]);
});
