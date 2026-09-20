import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const LOCALES = ["en", "ha", "ig", "yo"] as const;
const ORIGIN = "http://127.0.0.1:3101";
const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000002";

const overflow = (page: Page) =>
  page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);

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

async function startReviewerRun(page: Page, scenario = ""): Promise<void> {
  await page.waitForLoadState("networkidle");
  if (scenario !== "")
    await page.getByLabel(/Optional public search terms|public search terms/i).fill(scenario);
  await page.getByRole("button", { name: /Prepare query for review/i }).click();
  await page.getByLabel("Outbound query").waitFor();
  await page.getByRole("button", { name: /Approve and start search/i }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Approve and start" }).click();
}

for (const locale of LOCALES) {
  test(`${locale} public Source Scout: results with analysis, a failure, and a cancelled run are accessible`, async ({
    page
  }) => {
    for (const slug of ["synthetic-record-full", "synthetic-project-02", "synthetic-project-03"]) {
      await page.goto(`/${locale}/projects/${slug}`);
      await page.waitForLoadState("networkidle");
      await page.locator("[data-slot=project-discovery] button").first().click();
      await expect(
        page.locator("[data-slot=public-discovery-results] [data-slot=discovery-source]").first()
      ).toBeVisible();
      await audit(page);
    }
  });

  test(`${locale} reviewer Source Scout: plan, results, analysis, follow-ups, and decisions are accessible`, async ({
    context,
    page
  }) => {
    await signInAs(context, ORIGIN);
    await page.goto(`/${locale}/reviewer/reports/${REPORT}`);
    await startReviewerRun(page);
    await expect(
      page.locator("[data-slot=discovery-run] [data-slot=discovery-source]").first()
    ).toBeVisible();
    await audit(page);
  });
}

test("the run's confirmations and the failure and cancelled states are accessible", async ({
  context,
  page
}, info) => {
  await signInAs(context, ORIGIN);
  await page.goto(`/en/reviewer/reports/${REPORT}`);
  await startReviewerRun(page, "zz-queued");
  await page
    .locator("[data-slot=discovery-run]")
    .getByRole("button", { name: "Cancel this run" })
    .click();
  await expect(page.getByRole("alertdialog")).toBeVisible();
  expect(
    (await new AxeBuilder({ page }).exclude("[data-base-ui-focus-guard]").analyze()).violations
  ).toEqual([]);
  await page.getByRole("alertdialog").getByRole("button", { name: "Cancel the run" }).click();
  await expect(page.locator("[data-slot=discovery-run]")).toHaveAttribute(
    "data-status",
    "cancelled"
  );
  await audit(page);
  expect(info.project.name.length).toBeGreaterThan(0);
});
