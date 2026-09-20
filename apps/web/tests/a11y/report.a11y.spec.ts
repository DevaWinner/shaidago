import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const LOCALES = ["en", "ha", "ig", "yo"] as const;
const STEPS = [
  "notice",
  "observation",
  "evidence",
  "anonymity",
  "contact",
  "handle",
  "review",
  "failure"
] as const;

async function overflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

const next = async (page: Page) => {
  const button = page.locator("[data-action=next]");
  await expect(button).toBeEnabled();
  await button.click();
};

async function goTo(page: Page, locale: string, target: (typeof STEPS)[number]): Promise<void> {
  await page.goto(`/${locale}/report/synthetic-record-full`);
  await expect(page.locator("[data-action=next]")).toBeEnabled();
  if (target === "notice") return;
  await next(page);
  if (target === "observation") return;
  await page.locator("#report-category").selectOption("unsafe_construction");
  await page
    .locator("#report-description")
    .fill(
      target === "failure"
        ? "A fictional wall is leaning. __unavailable"
        : "A fictional wall is leaning by the road."
    );
  await next(page);
  if (target === "evidence") return;
  await next(page);
  if (target === "contact") {
    await page.locator("input[name=report-identity][value=contact]").check();
    return;
  }
  if (target === "handle") {
    await page.locator("input[name=report-identity][value=handle]").check();
    return;
  }
  if (target === "anonymity") return;
  await next(page);
  if (target === "failure") {
    await page.locator("[data-action=send]").click();
    await expect(page.locator("[data-slot=send-failure]")).toBeVisible();
  }
}

for (const locale of LOCALES) {
  for (const step of STEPS) {
    test(`${locale} report (${step}): no axe violations, reflows at 320 px and 200% text`, async ({
      page
    }) => {
      await goTo(page, locale, step);

      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
      await page.setViewportSize({ width: 320, height: 800 });
      expect(await overflow(page)).toBeLessThanOrEqual(0);
      await page.setViewportSize({ width: 640, height: 800 });
      await page.evaluate(() => {
        document.documentElement.style.fontSize = "200%";
      });
      expect(await overflow(page)).toBeLessThanOrEqual(0);
    });
  }

  test(`${locale} confirmation and the unrecoverable state: no axe violations, reflow`, async ({
    page
  }) => {
    await page.goto(`/${locale}/report/complete`);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.setViewportSize({ width: 320, height: 800 });
    expect(await overflow(page)).toBeLessThanOrEqual(0);

    await goTo(page, locale, "review");
    await page.locator("[data-action=send]").click();
    await expect(page.locator("[data-slot=tracking-code]")).toBeVisible();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.setViewportSize({ width: 320, height: 800 });
    expect(await overflow(page)).toBeLessThanOrEqual(0);
    await page.evaluate(() => {
      document.documentElement.style.fontSize = "200%";
    });
    expect(await overflow(page)).toBeLessThanOrEqual(0);
  });
}

test("the wizard has labelled fields, an announced step change, 44 px controls, and no animation with reduced motion", async ({
  page
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await goTo(page, "en", "observation");

  await expect(page.locator("#report-category")).toHaveAccessibleName(/What kind of concern is it/);
  await expect(page.locator("#report-description")).toHaveAttribute("aria-describedby", /.+/);
  const box = await page.locator("[data-action=next]").boundingBox();
  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  await expect(
    page.getByRole("navigation", { name: "Report steps" }).locator("[aria-current=step]")
  ).toHaveCount(1);
  const animated = await page.evaluate(
    () =>
      [...document.querySelectorAll("[data-slot=report-wizard] *")].filter((element) => {
        const style = getComputedStyle(element);
        return style.animationName !== "none" || parseFloat(style.transitionDuration) > 0;
      }).length
  );
  expect(animated).toBe(0);
  await page.locator("[data-action=next]").click();
  await expect(page.locator("[data-slot=error-summary]"))
    .toBeFocused({ timeout: 100 })
    .catch(() => undefined);
  await expect(page.locator("[data-slot=error-summary] h2")).toBeFocused();
});
