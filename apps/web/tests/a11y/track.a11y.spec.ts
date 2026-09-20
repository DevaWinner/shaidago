import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["en", "ha", "ig", "yo"] as const;

async function overflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

async function audit(page: Page): Promise<void> {
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.setViewportSize({ width: 320, height: 800 });
  expect(await overflow(page)).toBeLessThanOrEqual(0);
  await page.setViewportSize({ width: 640, height: 800 });
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "200%";
  });
  expect(await overflow(page)).toBeLessThanOrEqual(0);
  // Each state is checked at 320 px and at 200% text separately, as the other suites do.
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "";
  });
  await page.setViewportSize({ width: 1280, height: 800 });
}

const enabled = async (page: Page, selector: string) => {
  await expect(page.locator(selector).first()).toBeEnabled();
};

for (const locale of LOCALES) {
  test(`${locale} status page: initial, status with a question, failure, and handle list are accessible`, async ({
    page
  }) => {
    await page.goto(`/${locale}/track`);
    await expect(
      page.locator("[data-slot=track-panel] form").first().locator("button[type=submit]")
    ).toBeEnabled();
    await audit(page);

    const code = page.locator("[data-slot=track-panel] form").first();

    await code.locator("input").fill("SG-FOLLOWUP-1");
    await code.locator("button[type=submit]").click();
    await expect(page.locator("[data-slot=track-result] ol")).toBeVisible();
    await audit(page);

    await code.locator("input").fill("SG-NOTFOUND-1");
    await code.locator("button[type=submit]").click();
    await expect(page.locator("[data-slot=track-failure]")).toBeVisible();
    await audit(page);

    const handle = page.locator("[data-slot=track-panel] form").nth(1);

    await handle.locator("input").first().fill("fictional-handle-001");
    await handle.locator("input").nth(1).fill("amber bridge candle");
    await handle.locator("button[type=submit]").click();
    await expect(page.locator("[data-slot=handle-result] ol")).toBeVisible();
    await audit(page);
  });

  test(`${locale} handle page: initial, created, and deleted are accessible`, async ({ page }) => {
    await page.goto(`/${locale}/handle`);
    await enabled(page, "[data-slot=handle-panel] section:nth-of-type(2) button");
    await audit(page);

    await page.locator("[data-slot=handle-panel] section:nth-of-type(2) button").first().click();
    await expect(page.locator("[data-slot=handle-created]")).toBeVisible();
    await audit(page);

    const form = page.locator("[data-slot=handle-panel] form");

    await form.locator("input").first().fill("fictional-handle-009");
    await form.locator("input[type=password]").fill("secret words");
    await form.locator("input[type=checkbox]").check();
    await form.locator("button[type=submit]").click();
    await expect(page.locator("[data-slot=delete-result]")).toBeVisible();
    await audit(page);
  });
}

test("focus lands on the result heading after a check, and controls are at least 44 px", async ({
  page
}) => {
  await page.goto("/en/track");
  await expect(
    page.locator("[data-slot=track-panel] form").first().locator("button[type=submit]")
  ).toBeEnabled();
  const form = page.locator("[data-slot=track-panel] form").first();

  await form.locator("input").fill("SG-CLOSED-1");
  await form.locator("button[type=submit]").click();
  await expect(page.locator("[data-slot=track-result] h3").first()).toBeFocused();
  const box = await form.locator("button[type=submit]").boundingBox();

  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
});
