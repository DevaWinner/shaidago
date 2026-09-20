import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("the foundation document has no automated axe violations", async ({ page }) => {
  await page.goto("/");

  const results = await new AxeBuilder({ page }).analyze();

  expect(results.violations).toEqual([]);
});
