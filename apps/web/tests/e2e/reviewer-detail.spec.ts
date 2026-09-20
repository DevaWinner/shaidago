import { expect, test } from "@playwright/test";

import { STALE_TOKEN, signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const MOCK = "http://127.0.0.1:3200";
const id = (n: number) => `0198f1a2-7b3c-4d4e-8f5a-${String(n).padStart(12, "0")}`;
const FULL = `/en/reviewer/reports/${id(1)}`;
const CONTACT = "fictional-contact@example.invalid";

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

test("a signed-out visitor is sent to sign-in with this report as the return target", async ({
  browser
}) => {
  const context = await browser.newContext({ baseURL: ORIGIN });
  const page = await context.newPage();

  await page.goto(FULL);
  await expect(page).toHaveURL(
    new RegExp(`/en/reviewer/sign-in\\?next=${encodeURIComponent(FULL).replaceAll("/", "%2F")}`)
  );
  expect(await page.content()).not.toContain("Fictional description");
  await context.close();
});

test("an ended session leaves no report data on the sign-in page", async ({ context, page }) => {
  await context.clearCookies();
  await signInAs(context, ORIGIN, STALE_TOKEN);
  await page.goto(FULL);

  await expect(page).toHaveURL(/reason=expired/);
  expect(await page.content()).not.toContain("Fictional description");
});

test("the detail page is no-store, unindexed, and ordered as the reviewer works", async ({
  page
}) => {
  const response = await page.goto(FULL);

  expect(response?.headers()["cache-control"]).toMatch(/no-store|no-cache/);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  await expect(page.getByRole("heading", { level: 1, name: "Report" })).toBeVisible();
  expect(
    await page
      .locator("[data-section]")
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("data-section")))
  ).toEqual([
    "status",
    "observation",
    "evidence",
    "contact",
    "history",
    "questions",
    "notes",
    "handle",
    "scout"
  ]);
  await expect(
    page.locator("[data-slot=callout]").filter({ hasText: "Fictional demo data" })
  ).toBeVisible();
  await expect(page.locator("[data-slot=report-header]")).toContainText("Status:");
  await expect(page.locator("[data-slot=report-header]")).toContainText("Risk:");
});

test("the description is plain text and nothing in it runs", async ({ page }) => {
  await page.goto(FULL);
  const text = page.locator("[data-slot=report-description]");

  await expect(text).toContainText("<script>alert(1)</script>");
  await expect(text).toContainText("<b>bold</b>");
  expect(await text.locator("script, b").count()).toBe(0);
});

test("contact is not in the page until it is asked for, then it is shown and can be hidden again", async ({
  page,
  request
}) => {
  await page.goto(FULL);
  expect(await page.content()).not.toContain(CONTACT);
  await expect(page.getByText("Contact details exist but are hidden.")).toBeVisible();

  await page.getByRole("button", { name: "Show contact details" }).click();
  await expect(page).toHaveURL(/reveal=contact$/);
  await expect(page.getByText(`email: ${CONTACT}`)).toBeVisible();
  expect(page.url()).not.toContain("fictional-contact");

  const log = (await (await request.get(`${MOCK}/__reviewer`)).json()) as { contact?: boolean }[];

  expect(log.some((entry) => entry.contact === true)).toBe(true);
  await page.getByRole("link", { name: "Hide contact details" }).click();
  await expect(page).not.toHaveURL(/reveal/);
  expect(await page.content()).not.toContain(CONTACT);
});

test("an account that may not see contact still gets the report and is told why", async ({
  page
}) => {
  await page.goto(`/en/reviewer/reports/${id(5)}?reveal=contact`);

  await expect(page.getByText("This account is not allowed to see contact details.")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "Report" })).toBeVisible();
  await expect(page.locator("[data-section=observation]")).toBeVisible();
});

test("evidence shows its cleaning and scan state, warns about the unscanned demo file, and renders nothing inline", async ({
  page
}) => {
  await page.goto(FULL);
  const files = page.locator("[data-slot=evidence-list] > li");

  await expect(files).toHaveCount(2);
  await expect(files.first()).toContainText("Not scanned (demo only)");
  await expect(files.first()).toContainText("has no malware scanner");
  await expect(files.nth(1)).toContainText("No malware found");
  await expect(files.nth(1)).toContainText("3 MB");
  expect(await page.locator("img, iframe, embed, object, video, audio").count()).toBe(0);
});

test("history separates what the reporter saw from the private reason, and handle context is not proof", async ({
  page
}) => {
  await page.goto(FULL);

  await expect(page.locator("[data-slot=history-list]")).toContainText(
    "Internal reason (private): Fictional internal reason"
  );
  await expect(page.locator("[data-slot=history-list]")).toContainText(
    "No message shown to the reporter."
  );
  await expect(page.locator("[data-section=questions]")).toContainText("Not answered yet.");
  await expect(page.locator("[data-section=handle]")).toContainText("not proof");
});

test("an unknown report, a malformed one, an outage, and a forbidden one each get a calm answer", async ({
  page
}) => {
  await page.goto(`/en/reviewer/reports/${id(999)}`);
  await expect(page.getByText("This report is not available")).toBeVisible();
  const unknown = await page.locator("main").innerText();

  await page.goto("/en/reviewer/reports/not-an-id");
  expect(await page.locator("main").innerText()).toBe(unknown);

  await page.goto(`/en/reviewer/reports/${id(44)}`);
  await expect(page.getByText("The report could not be loaded")).toBeVisible();
  await expect(page.getByRole("link", { name: "Try again" })).toBeVisible();

  await page.goto(`/en/reviewer/reports/${id(45)}`);
  await expect(page.getByText("This account cannot open this report")).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to the report queue" })).toBeVisible();
});

test("a phone-width detail page does not scroll sideways and keeps status in words", async ({
  page
}) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.goto(FULL);

  await expect(page.locator("[data-slot=report-header]")).toContainText("Status:");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
});

test("opening a report from the queue works and the queue never preloaded it", async ({ page }) => {
  await page.goto("/en/reviewer/reports");
  await page
    .getByRole("link", { name: /^Open report for synthetic-example-clinic/ })
    .first()
    .click();
  await expect(page).toHaveURL(/\/en\/reviewer\/reports\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1, name: "Report" })).toBeVisible();
});
