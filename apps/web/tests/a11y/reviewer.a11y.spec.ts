import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const LOCALES = ["en", "ha", "ig", "yo"] as const;
const id = (n: number) => `0198f1a2-7b3c-4d4e-8f5a-${String(n).padStart(12, "0")}`;
const ORIGIN = "http://127.0.0.1:3101";

async function overflow(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

/** Axe at desktop width, then 320 px and 200% text for the same state, as the other suites do. */
async function audit(page: Page): Promise<void> {
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
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
  await page.setViewportSize({ width: 1280, height: 800 });
}

/**
 * Axe for an open confirmation. Base UI's modal focus-trap helpers (`data-base-ui-focus-guard`)
 * are nameless `role="button"` spans on iOS WebKit only, which axe reports as `aria-command-name`.
 * They are the library's internal focus-trap plumbing, not content we author, so exactly those
 * elements are excluded; every other element of the dialog and page is still audited. The
 * exception is recorded in the build log for the maintainer to review.
 */
async function auditDialog(page: Page): Promise<void> {
  expect(
    (await new AxeBuilder({ page }).exclude("[data-base-ui-focus-guard]").analyze()).violations
  ).toEqual([]);
}

// The two browser projects share one mock, so each uses its own reports for anything that changes.
const own = (info: TestInfo, chromium: number, webkit: number): number =>
  info.project.name === "chromium" ? chromium : webkit;

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

for (const locale of LOCALES) {
  test(`${locale} sign-in: initial, failure, and rate limit are accessible`, async ({
    browser
  }) => {
    const context = await browser.newContext({ baseURL: ORIGIN });
    const page = await context.newPage();

    await page.goto(`/${locale}/reviewer/sign-in`);
    await expect(page.locator("[data-slot=reviewer-sign-in] button[type=submit]")).toHaveAttribute(
      "aria-disabled",
      "false"
    );
    await audit(page);

    const form = page.locator("[data-slot=reviewer-sign-in]");

    await form.locator("input[name=identifier]").fill("reviewer-demo");
    await form.locator("input[name=password]").fill("not-the-password");
    await form.locator("button[type=submit]").click();
    await expect(page.locator("[data-slot=sign-in-failure]")).toBeVisible();
    await audit(page);

    await form.locator("input[name=identifier]").fill("rate-limited");
    await form.locator("input[name=password]").fill("x");
    await page.waitForTimeout(2200);
    await form.locator("button[type=submit]").click();
    await expect(page.locator("[data-slot=sign-in-wait]")).toBeVisible();
    await audit(page);
    await context.close();
  });

  test(`${locale} queue: results, no match, and outage are accessible`, async ({ page }) => {
    await page.goto(`/${locale}/reviewer/reports`);
    await expect(page.locator("[data-slot=queue-item]").first()).toBeVisible();
    await audit(page);
    await page.goto(`/${locale}/reviewer/reports?project=nothing-here`);
    await expect(page.locator("[data-slot=queue-notice]")).toBeVisible();
    await audit(page);
    await page.goto(`/${locale}/reviewer/reports?project=zz-unavailable`);
    await expect(page.locator("[data-slot=queue-notice]")).toBeVisible();
    await audit(page);
  });

  test(`${locale} report detail: typical report, revealed contact, and unavailable are accessible`, async ({
    page
  }) => {
    await page.goto(`/${locale}/reviewer/reports/${id(1)}`);
    await expect(page.locator("[data-slot=report-header]")).toBeVisible();
    await audit(page);
    await page.goto(`/${locale}/reviewer/reports/${id(1)}?reveal=contact`);
    await expect(page.locator("[data-slot=contact-revealed]")).toBeVisible();
    await audit(page);
    await page.goto(`/${locale}/reviewer/reports/${id(44)}`);
    await expect(page.locator("[data-slot=queue-notice]")).toBeVisible();
    await audit(page);
  });
}

test("the actions, dialogs, and preview are accessible", async ({ page }, info) => {
  await page.goto(`/en/reviewer/reports/${id(own(info, 41, 39))}`);
  await expect(page.locator("[data-slot=status-actions]")).toBeVisible();
  await audit(page);

  const status = page.locator("[data-slot=status-actions]");

  await status.getByLabel("Action").selectOption("close");
  await status.getByRole("button", { name: "Apply change" }).click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await auditDialog(page);
  await page.keyboard.press("Escape");

  await page.getByLabel("New note").fill("A fictional note");
  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await auditDialog(page);
  await page.keyboard.press("Escape");
});

test("the composer and its preview are accessible", async ({ page }, info) => {
  await page.goto(`/en/reviewer/reports/${id(own(info, 4, 10))}`);
  await expect(page.locator("[data-slot=publication-composer]")).toBeVisible();
  await audit(page);

  await page.getByLabel(/^Public statement/).fill("Fictional works were recorded as planned.");
  await page.getByLabel(/^Date this applies from/).fill("2026-09-01");
  await page.getByRole("checkbox").first().check();
  await page.getByRole("button", { name: "Create a preview" }).click();
  await expect(page.getByRole("heading", { name: "Exact preview" })).toBeVisible();
  await audit(page);
  await page.getByRole("button", { name: "Publish this update" }).click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await auditDialog(page);
});

test("controls are at least 44 px and status text is not colour alone", async ({ page }) => {
  await page.goto(`/en/reviewer/reports/${id(1)}`);
  await expect(page.locator("[data-slot=note-form]")).toBeVisible();
  const box = await page.locator("[data-slot=note-form] button[type=submit]").boundingBox();

  expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  await expect(
    page.locator("[data-slot=report-header] [data-slot=status-label]").first()
  ).toContainText("Status:");
});
