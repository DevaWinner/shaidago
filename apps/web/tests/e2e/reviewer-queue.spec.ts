import { expect, test } from "@playwright/test";

import { STALE_TOKEN, signInAs } from "../support/reviewer-session";

const QUEUE = "/en/reviewer/reports";
const ORIGIN = "http://127.0.0.1:3100";

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

test("a signed-out visitor is sent to sign-in and sees no queue", async ({ browser }) => {
  const context = await browser.newContext({ baseURL: ORIGIN });
  const page = await context.newPage();

  await page.goto(QUEUE);
  await expect(page).toHaveURL(/\/en\/reviewer\/sign-in$/);
  await expect(page.locator("[data-slot=queue-item]")).toHaveCount(0);
  await context.close();
});

test("an ended session returns to sign-in with a generic explanation and no queue data", async ({
  context,
  page
}) => {
  await context.clearCookies();
  await signInAs(context, ORIGIN, STALE_TOKEN);
  await page.goto(QUEUE);

  await expect(page).toHaveURL(/\/en\/reviewer\/sign-in\?reason=expired$/);
  await expect(page.getByText("Your session ended. Sign in again to continue.")).toBeVisible();
  await expect(page.locator("[data-slot=queue-item]")).toHaveCount(0);
  expect(await page.content()).not.toContain("synthetic-example");
});

test("the queue is no-store, unindexed, and shows only triage facts", async ({ page }) => {
  const response = await page.goto(QUEUE);

  expect(response?.headers()["cache-control"]).toMatch(/no-store|no-cache/);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  await expect(page.getByRole("heading", { level: 1, name: "Report queue" })).toBeVisible();
  await expect(page.locator("[data-slot=queue-item]")).toHaveCount(20);

  const first = page.locator("[data-slot=queue-item]").first();

  await expect(first).toContainText("Status:");
  await expect(first).toContainText("Risk:");
  await expect(first).toContainText("Received 1 September 2026");
  await expect(first.getByRole("link", { name: /^Open report for / })).toHaveAttribute(
    "href",
    /^\/en\/reviewer\/reports\/[0-9a-f-]{36}$/
  );
});

test("cursor pages continue the list and going back to the first page is offered", async ({
  page
}) => {
  await page.goto(QUEUE);
  await page.getByRole("link", { name: "Next reports" }).click();
  await expect(page).toHaveURL(/cursor=/);
  await expect(page.locator("[data-slot=queue-item]")).toHaveCount(20);
  await page.getByRole("link", { name: "Next reports" }).click();
  await expect(page.locator("[data-slot=queue-item]")).toHaveCount(5);
  await expect(page.getByRole("link", { name: "Next reports" })).toHaveCount(0);
  await page.getByRole("link", { name: "Back to the first page" }).click();
  await expect(page).not.toHaveURL(/cursor=/);
});

test("filters live in the address, drop unknown values, and start again from the first page", async ({
  page
}) => {
  await page.goto(`${QUEUE}?status=bogus&unknown=1`);
  await expect(page.locator("[data-slot=queue-item]")).toHaveCount(20);

  await page.getByLabel("Status").selectOption("under_review");
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expect(page).toHaveURL(/status=under_review/);
  const rows = page.locator("[data-slot=queue-item]");

  expect(await rows.count()).toBeGreaterThan(0);
  for (const status of await rows.evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute("data-report-status"))
  )) {
    expect(status).toBe("under_review");
  }
});

test("a filter with no match and an empty filter result say so and offer a way back", async ({
  page
}) => {
  await page.goto(`${QUEUE}?project=nothing-here`);
  await expect(page.getByText("No reports match these filters")).toBeVisible();
  await page.getByRole("link", { name: "Clear filters" }).first().click();
  await expect(page.locator("[data-slot=queue-item]")).toHaveCount(20);
});

test("a cursor from other filters is refused with a way back", async ({ page }) => {
  await page.goto(QUEUE);
  const href = await page.getByRole("link", { name: "Next reports" }).getAttribute("href");
  const cursor = new URL(href ?? "", "http://x").searchParams.get("cursor") ?? "";

  await page.goto(`${QUEUE}?risk=high&cursor=${encodeURIComponent(cursor)}`);
  await expect(page.getByText("That page is no longer valid")).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to the first page" })).toBeVisible();
});

test("forbidden, rate-limited, and unavailable outcomes are different and keep the page usable", async ({
  page
}) => {
  await page.goto(`${QUEUE}?project=zz-forbidden`);
  await expect(page.getByText("This account cannot open the queue")).toBeVisible();
  await page.goto(`${QUEUE}?project=zz-limited`);
  await expect(page.getByText("Too many requests")).toBeVisible();
  await page.goto(`${QUEUE}?project=zz-unavailable`);
  await expect(page.getByText("The queue could not be loaded")).toBeVisible();
  await expect(page.getByRole("link", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Apply filters" })).toBeVisible();
});

test("a phone-width queue keeps status and risk in text and does not scroll sideways", async ({
  page
}) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.goto(QUEUE);
  const first = page.locator("[data-slot=queue-item]").first();

  await expect(
    first.locator("[data-slot=status-label]").filter({ hasText: "Status: " })
  ).toBeVisible();
  await expect(
    first.locator("[data-slot=status-label]").filter({ hasText: "Risk: " })
  ).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
});

test("the queue links do not prefetch private pages", async ({ page }) => {
  const requests: string[] = [];

  page.on("request", (request) => requests.push(request.url()));
  await page.goto(QUEUE);
  await page.waitForTimeout(500);
  expect(requests.some((url) => /\/reviewer\/reports\/[0-9a-f-]{36}/.test(url))).toBe(false);
});

test("on a phone the first queue row is visible without scrolling past the filters", async ({
  page
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(QUEUE);
  const box = await page.locator("[data-slot=queue-item]").first().boundingBox();

  expect(box?.y ?? Infinity).toBeLessThan(844);
});
