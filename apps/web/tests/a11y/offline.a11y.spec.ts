import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const locale of ["en", "ha", "ig", "yo"] as const) {
  test(`${locale} offline page is accessible at 320 px and 200% text`, async ({ page }) => {
    await page.goto(`/${locale}/offline`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.setViewportSize({ width: 320, height: 800 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      )
    ).toBeLessThanOrEqual(0);
    await page.setViewportSize({ width: 640, height: 800 });
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "200%";
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      )
    ).toBeLessThanOrEqual(0);
  });
}
