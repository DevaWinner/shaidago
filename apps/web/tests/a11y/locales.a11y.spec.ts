import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const LOCALES = ["en", "ha", "ig", "yo"] as const;

for (const locale of LOCALES) {
  test(`${locale}: no automated axe violations`, async ({ page }) => {
    await page.goto(`/${locale}`);

    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  });

  test(`${locale}: long copy reflows at 320 px and at 200% text without horizontal scrolling or clipping`, async ({
    page
  }) => {
    await page.goto(`/${locale}`);
    const overflow = () =>
      page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      );

    await page.setViewportSize({ width: 320, height: 800 });
    expect(await overflow()).toBeLessThanOrEqual(0);

    await page.setViewportSize({ width: 640, height: 800 });
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "200%";
    });
    expect(await overflow()).toBeLessThanOrEqual(0);

    // No control may hide part of its label.
    const clipped = await page.$$eval("a, button", (elements) =>
      elements
        .filter((element) => element.scrollWidth > element.clientWidth + 1)
        .map((element) => element.textContent?.trim())
    );
    expect(clipped).toEqual([]);
  });
}
