import { progressSlug } from "../support/progress-slug";
import { expect, test, type Page } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000002";
const panel = (page: Page) => page.locator("[data-slot=project-discovery]");

async function startPublic(page: Page, slug: string): Promise<void> {
  await page.goto(`/en/projects/${slug}`);
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find public information" }).click();
}

test("a flapping connection during a public run resumes the same run and never starts a second one", async ({
  context,
  page
}, info) => {
  let posts = 0;

  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/public/discovery")) posts += 1;
  });
  await startPublic(page, progressSlug(info));
  await expect(panel(page)).toContainText("Searching public sources");

  for (let flap = 0; flap < 3; flap += 1) {
    await context.setOffline(true);
    await page.evaluate(() => window.dispatchEvent(new Event("offline")));
    await expect(panel(page)).toContainText("You are offline");
    await page.waitForTimeout(400);
    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event("online")));
  }

  await expect(panel(page)).toContainText("Search completed", { timeout: 25000 });
  await expect(panel(page)).not.toContainText("You are offline");
  expect(posts).toBe(1);
});

test("pressing start twice sends one request and makes one run", async ({ page }) => {
  let posts = 0;

  page.on("request", (request) => {
    if (request.method() === "POST" && request.url().endsWith("/api/public/discovery")) posts += 1;
  });
  await page.goto("/en/projects/synthetic-record-full");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find public information" }).dblclick();
  await expect(panel(page).locator("[data-slot=discovery-source]").first()).toBeVisible();
  expect(posts).toBe(1);
});

test("a read that never answers is abandoned after a bounded wait, and can be retried", async ({
  page
}, info) => {
  // In Playwright's WebKit a request held by a route handler is not released when the page aborts
  // it, so the timeout is proven end to end on Chromium and by the unit tests of `withTimeout`.
  test.skip(
    info.project.name !== "chromium",
    "Playwright WebKit does not release a route-held request on abort"
  );
  test.setTimeout(45000);
  let hang = true;

  await page.route("**/api/public/discovery/*", async (route) => {
    if (hang) {
      await new Promise((resolve) => setTimeout(resolve, 20000));
      await route.abort().catch(() => undefined);
    } else {
      await route.continue();
    }
  });
  await startPublic(page, "synthetic-record-full");
  await expect(panel(page)).toContainText("Could not reach ShaidaGo", { timeout: 15000 });
  hang = false;
  await panel(page).getByRole("button", { name: "Find public information" }).click();
  await expect(panel(page).locator("[data-slot=discovery-source]").first()).toBeVisible();
});

test("a run that says 'not modified' keeps being checked instead of silently stopping", async ({
  context,
  page
}) => {
  test.setTimeout(30000);
  const reads: number[] = [];

  await signInAs(context, ORIGIN);
  page.on("request", (request) => {
    if (/\/api\/reviewer\/discovery\/[0-9a-f-]{36}/.test(request.url())) reads.push(Date.now());
  });
  await page.goto(`/en/reviewer/reports/${REPORT}`);
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Optional public search terms").fill("zz-queued");
  await page.getByRole("button", { name: "Prepare query for review" }).click();
  await page.getByLabel("Outbound query").waitFor();
  await page.getByRole("button", { name: "Approve and start search" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Approve and start" }).click();
  await expect(page.locator("[data-slot=discovery-run]")).toHaveAttribute("data-status", "queued");
  await expect.poll(() => reads.length, { timeout: 16000 }).toBeGreaterThanOrEqual(4);
  const gaps = reads.slice(1).map((time, index) => time - (reads[index] ?? time));

  expect(gaps.every((gap) => gap >= 1500)).toBe(true);
});

test("offline before a mutation sends nothing and says so; the words are kept and it goes when the connection returns", async ({
  context,
  page
}) => {
  await page.goto("/en/projects/synthetic-record-full");
  await page.waitForLoadState("networkidle");
  const question = page.getByLabel("Your question");
  let sent = 0;

  page.on("request", (request) => {
    if (request.url().endsWith("/api/public/questions")) sent += 1;
  });
  await question.fill("What is the cited start date?");
  await context.setOffline(true);
  await page
    .getByRole("button", { name: /Ask|Send/i })
    .first()
    .click();
  await expect(page.locator("[data-slot=project-question]")).toContainText(
    /connection|offline|Could not reach/i
  );
  expect(await question.inputValue()).toBe("What is the cited start date?");
  await context.setOffline(false);
  await page
    .getByRole("button", { name: /Ask|Send|try again/i })
    .first()
    .click();
  await expect(page.locator("[data-slot=question-result]").first()).toBeVisible({ timeout: 10000 });
  expect(sent).toBeGreaterThanOrEqual(1);
});

test("back online after a saved page, the notice says so and a reload fetches the current page", async ({
  context,
  page
}, info) => {
  test.skip(
    info.project.name !== "chromium",
    "Playwright WebKit cannot emulate offline navigation with a service worker"
  );
  await page.goto("/en");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.goto("/en/projects/synthetic-record-full");
  await page.waitForLoadState("networkidle");
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await expect(page.locator("[data-slot=offline-banner]")).toBeVisible();
  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(page.getByText("You are back online.")).toBeVisible();
  await expect(page.locator("[data-slot=offline-banner]")).toHaveCount(0);
});
