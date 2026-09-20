import { progressSlug } from "../support/progress-slug";
import { expect, test } from "@playwright/test";

test("a resident starts a bounded public discovery replay without putting state in the address", async ({
  page
}) => {
  await page.goto("/en/projects/synthetic-record-full");
  const before = page.url();

  await page.getByRole("button", { name: "Find public information" }).click();

  await expect(page.getByText("Search completed").first()).toBeVisible();
  await expect(page.getByText("Found 3; fetched 3; analysed 2.")).toBeVisible();
  await expect(page.getByText("Showing a fictional replay for the demo.")).toBeVisible();
  expect(page.url()).toBe(before);
  expect(await page.locator("progress").count()).toBe(0);
  const html = (await page.content()).toLowerCase();
  for (const privateTerm of [
    "tracking_code",
    "contact_value",
    "reviewer_note",
    "internal_reason"
  ]) {
    expect(html).not.toContain(privateTerm);
  }
});

test("a resident is told when a public discovery run is unavailable", async ({ page }) => {
  await page.goto("/en/projects/synthetic-record-minimal");

  await page.getByRole("button", { name: "Find public information" }).click();

  await expect(page.getByText("A public search is not available right now.")).toBeVisible();
});

const panel = (page: import("@playwright/test").Page) =>
  page.locator("[data-slot=project-discovery]");
const start = async (page: import("@playwright/test").Page, slug: string) => {
  await page.goto(`/en/projects/${slug}`);
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find public information" }).click();
};

test("public results are labelled unreviewed, show provenance, and keep analysis apart", async ({
  page
}) => {
  await start(page, "synthetic-record-full");
  const results = page.locator("[data-slot=public-discovery-results]");

  await expect(results.locator("[data-slot=discovery-source]")).toHaveCount(3);
  for (const card of await results.locator("[data-slot=discovery-source]").all()) {
    await expect(card).toContainText("discovered — not yet reviewed");
  }
  await expect(results).toContainText("Published 1 September 2026 (page metadata)");
  await expect(results).toContainText("The pages disagree about this date.");
  await expect(results.locator("[data-slot=discovery-analysis]")).toContainText(
    "an explanation, not a source"
  );
  expect(await page.locator("a[href^='javascript']").count()).toBe(0);
  await expect(panel(page).getByRole("button", { name: /Cancel/ })).toHaveCount(0);
  await expect(panel(page).getByLabel(/answer/i)).toHaveCount(0);
});

test("a spent budget shows the latest run with its failure, and a cancelled run says its results are partial", async ({
  page
}) => {
  await start(page, "synthetic-project-02");
  await expect(panel(page)).toContainText("The daily search budget is used up");
  await expect(panel(page).locator("[data-slot=discovery-source]")).toHaveCount(1);
  await start(page, "synthetic-project-03");
  await expect(panel(page)).toContainText(
    "Anything found before cancelling is shown below and is incomplete."
  );
});

test("an unverifiable analysis is not shown, and progress stops polling when the run finishes", async ({
  page
}, info) => {
  await start(page, "synthetic-project-05");
  await expect(panel(page)).toContainText("No analysis is shown");
  await expect(panel(page).locator("[data-slot=discovery-analysis]")).toHaveCount(0);

  const reads: string[] = [];

  page.on("request", (request) => {
    if (request.url().includes("/api/public/discovery/")) reads.push(request.url());
  });
  await start(page, progressSlug(info));
  await expect(panel(page)).toContainText("Search completed", { timeout: 14000 });
  const settled = reads.length;

  await page.waitForTimeout(3500);
  expect(reads.length).toBe(settled);
  expect(await panel(page).locator("progress, [role=progressbar]").count()).toBe(0);
});

test("going offline keeps public results on screen and says so", async ({ context, page }) => {
  await start(page, "synthetic-record-full");
  await expect(panel(page).locator("[data-slot=discovery-source]").first()).toBeVisible();
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await expect(panel(page)).toContainText("You are offline");
  await expect(panel(page).locator("[data-slot=discovery-source]").first()).toBeVisible();
  await context.setOffline(false);
});
