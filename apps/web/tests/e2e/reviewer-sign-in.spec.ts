import { expect, test, type Page } from "@playwright/test";

const SIGN_IN = "/en/reviewer/sign-in";
const IDENTIFIER = "reviewer-demo";
const PASSWORD = "fictional-password-not-a-secret";
const REPORT = "0198f1a2-7b3c-4d4e-8f5a-123456789abc";

async function ready(page: Page, path = SIGN_IN): Promise<void> {
  await page.goto(path);
  await expect(page.getByRole("button", { name: "Sign in" })).toHaveAttribute(
    "aria-disabled",
    "false"
  );
}

async function fill(page: Page, identifier: string, password: string): Promise<void> {
  await page.getByLabel(/^Reviewer identifier/).fill(identifier);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("the sign-in page is no-store, unindexed, and never lists a token", async ({ page }) => {
  const response = await page.goto(SIGN_IN);

  expect(response?.headers()["cache-control"]).toMatch(/no-store|no-cache/);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
    "content",
    /noindex.*nofollow|nofollow.*noindex/
  );
  await expect(page.getByRole("heading", { level: 1, name: "Reviewer sign-in" })).toBeVisible();
  await expect(page.getByLabel(/^Password/)).toHaveAttribute("type", "password");
  expect(await page.content()).not.toContain("fictional-session-token");
});

test("a wrong credential gets one generic message and leaves no cookie or stored value", async ({
  page
}) => {
  await ready(page);
  await fill(page, IDENTIFIER, "not-the-password");

  const alert = page.getByRole("alert").filter({ hasText: "Sign-in did not work" });

  await expect(alert).toContainText("Those details were not accepted");
  await expect(page.getByLabel(/^Password/)).toHaveValue("");
  expect(page.url()).not.toContain("not-the-password");
  expect(await page.context().cookies()).toEqual([]);
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).toBe(
    "{}"
  );
});

test("a rate limit shows the wait and holds the button", async ({ page }) => {
  await ready(page);
  await fill(page, "rate-limited", "anything");

  await expect(page.locator("[data-slot=sign-in-wait]")).toContainText("try again in");
  await expect(page.getByRole("button", { name: "Sign in" })).toHaveAttribute(
    "aria-disabled",
    "true"
  );
});

test("sign-in sets HttpOnly cookies the page cannot read and lands on the queue", async ({
  page
}) => {
  await ready(page);
  await fill(page, IDENTIFIER, PASSWORD);
  await page.waitForURL("**/en/reviewer/reports");

  const cookies = await page.context().cookies();
  const session = cookies.find((cookie) => cookie.name === "sg_session");

  expect(session?.httpOnly).toBe(true);
  expect(session?.sameSite).toBe("Lax");
  expect(await page.evaluate(() => document.cookie)).not.toContain("sg_session");
  expect(page.url()).not.toContain(PASSWORD);
});

test("the return target cannot be an open redirect, and a report target is honoured", async ({
  page
}) => {
  await ready(page, `${SIGN_IN}?next=${encodeURIComponent("//evil.example/x")}`);
  await fill(page, IDENTIFIER, PASSWORD);
  await page.waitForURL("**/en/reviewer/reports");
  expect(new URL(page.url()).origin).toBe(new URL(SIGN_IN, page.url()).origin);

  await page.context().clearCookies();
  await ready(page, `${SIGN_IN}?next=${encodeURIComponent(`/en/reviewer/reports/${REPORT}`)}`);
  await fill(page, IDENTIFIER, PASSWORD);
  await page.waitForURL(`**/en/reviewer/reports/${REPORT}`);
});

test("an ended session explains itself without showing any earlier page data", async ({ page }) => {
  await page.goto(`${SIGN_IN}?reason=expired`);
  await expect(page.getByText("Your session ended. Sign in again to continue.")).toBeVisible();
  await page.goto(`${SIGN_IN}?reason=%3Cscript%3E`);
  await expect(page.getByText("Your session ended.")).toHaveCount(0);
});
