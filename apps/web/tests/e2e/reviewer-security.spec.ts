import { expect, test, type ConsoleMessage } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const id = (n: number) => `0198f1a2-7b3c-4d4e-8f5a-${String(n).padStart(12, "0")}`;
const FULL = `/en/reviewer/reports/${id(1)}`;
const PASSWORD = "fictional-password-not-a-secret";
const PRIVATE = [
  "Fictional description line one",
  "fictional-contact@example.invalid",
  "Seeded fictional note",
  "Fictional internal reason",
  PASSWORD
];

test("a mutation without a session is refused and never reaches the API", async ({ request }) => {
  const response = await request.post(`/api/reviewer/reports/${id(3)}/notes`, {
    data: { body: "no session" },
    headers: { Origin: ORIGIN }
  });

  expect(response.status()).toBe(401);
  expect(response.headers()["cache-control"]).toContain("no-store");
  expect((await response.json()).code).toBe("unauthenticated");
});

test("a mutation with a session but no CSRF cookie is refused, in the browser and at the boundary", async ({
  context,
  page
}) => {
  await context.addCookies([
    {
      name: "sg_session",
      value: "fictional-session-token-0123456789abcdef",
      url: ORIGIN,
      httpOnly: true,
      sameSite: "Lax"
    }
  ]);
  const direct = await page.request.post(`/api/reviewer/reports/${id(3)}/notes`, {
    data: { body: "no csrf" },
    headers: { Origin: ORIGIN }
  });

  expect([401, 403]).toContain(direct.status());
  await page.goto(`/en/reviewer/reports/${id(3)}`);
  await page.getByLabel("New note").fill("A note without a CSRF cookie");
  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Add note" }).click();
  await expect(page.locator("[data-section=notes] [role=alert]")).toBeVisible();
  await expect(page.locator("[data-section=notes] [role=alert]")).toContainText(
    "could not be verified"
  );
  await expect(
    page.locator("[data-slot=notes-list]").filter({ hasText: "without a CSRF cookie" })
  ).toHaveCount(0);
});

test("a mutation from another origin is refused for every reviewer action", async ({
  context,
  request
}) => {
  await signInAs(context, ORIGIN);
  const evil = { Origin: "http://evil.example" };
  const targets = [
    [`/api/reviewer/reports/${id(3)}/notes`, { body: "x" }],
    [
      `/api/reviewer/reports/${id(3)}/status-transition`,
      { command: "close", expected_status: "received", expected_version: 1 }
    ],
    [`/api/reviewer/reports/${id(3)}/follow-up-questions`, { question: "Is this fictional?" }],
    [
      `/api/reviewer/reports/${id(3)}/public-updates/${id(9)}/publish`,
      { preview_digest: "a".repeat(64) }
    ]
  ] as const;

  for (const [path, data] of targets) {
    const response = await request.post(path, { data, headers: evil });

    expect(response.status(), path).toBe(403);
  }
});

test("signing out clears the cookies, records the CSRF-checked call, and going back shows no report", async ({
  context,
  page,
  request
}) => {
  await signInAs(context, ORIGIN);
  await page.goto(FULL);
  await expect(page.locator("[data-slot=report-description]")).toContainText(
    "Fictional description"
  );

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/en\/reviewer\/sign-in\?reason=signed_out$/);
  expect((await context.cookies()).filter((cookie) => cookie.name.startsWith("sg_"))).toEqual([]);
  const log = (await (await request.get("http://127.0.0.1:3200/__reviewer")).json()) as {
    op: string;
    csrf?: boolean;
  }[];

  expect(log.some((entry) => entry.op === "sign_out" && entry.csrf === true)).toBe(true);

  await page.goBack();
  await page.waitForLoadState("networkidle");
  expect(await page.content()).not.toContain("Fictional description");
  await expect(page).toHaveURL(/sign-in/);
  await page.goto(FULL);
  await expect(page).toHaveURL(/sign-in/);
});

test("reviewer responses are no-store, and private routes stay out of the public site", async ({
  context,
  page,
  request
}) => {
  await signInAs(context, ORIGIN);
  const evidence = await page.request.get(`/api/reviewer/reports/${id(1)}/evidence/${id(0)}`);

  expect(evidence.headers()["cache-control"]).toContain("no-store");
  for (const path of ["/en/reviewer/reports", FULL, "/en/reviewer/sign-in"]) {
    const response = await page.request.get(path);

    expect(response.headers()["cache-control"], path).toMatch(/no-store|no-cache/);
    expect(response.headers()["x-robots-tag"] ?? (await response.text()), path).toMatch(/noindex/);
  }

  const robots = await (await request.get("/robots.txt")).text();

  expect(robots).toContain("Disallow: /*/reviewer/");
  const home = await (await request.get("/en")).text();

  expect(home).not.toContain("/reviewer");
});

test("nothing private reaches the console or a page error during a reviewer session", async ({
  context,
  page
}) => {
  const seen: string[] = [];
  const record = (message: ConsoleMessage) => seen.push(message.text());

  page.on("console", record);
  page.on("pageerror", (error) => seen.push(error.message));
  await signInAs(context, ORIGIN);
  await page.goto("/en/reviewer/reports");
  await page.goto(FULL);
  await page.getByRole("button", { name: "Show contact details" }).click();
  await page.getByLabel("New note").fill("A fictional note for the console check");
  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Keep editing" }).click();

  for (const value of PRIVATE) {
    expect(seen.join("\n")).not.toContain(value);
  }
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).toBe(
    "{}"
  );
});

test("a keyboard user can sign in, open a report from the queue, and reach the actions", async ({
  page
}, info) => {
  test.skip(info.project.name !== "chromium", "Tab focus differs on iOS WebKit");
  await page.goto("/en/reviewer/sign-in");
  await expect(page.getByRole("button", { name: "Sign in" })).toHaveAttribute(
    "aria-disabled",
    "false"
  );
  await page.getByLabel(/^Reviewer identifier/).focus();
  await page.keyboard.type("reviewer-demo");
  await page.keyboard.press("Tab");
  await page.keyboard.type(PASSWORD);
  await page.keyboard.press("Enter");
  await page.waitForURL("**/en/reviewer/reports");

  const link = page.getByRole("link", { name: /^Open report for / }).first();

  for (
    let step = 0;
    step < 80 && !(await link.evaluate((node) => node === document.activeElement));
    step += 1
  ) {
    await page.keyboard.press("Tab");
  }
  await expect(link).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/en\/reviewer\/reports\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { level: 1, name: "Report" })).toBeVisible();

  const apply = page
    .locator("[data-slot=status-actions]")
    .getByRole("button", { name: "Apply change" });

  for (
    let step = 0;
    step < 120 && !(await apply.evaluate((node) => node === document.activeElement));
    step += 1
  ) {
    await page.keyboard.press("Tab");
  }
  await expect(apply).toBeFocused();
});

test("focus returns to the control that opened a confirmation, and the skip link reaches the main content", async ({
  context,
  page
}, info) => {
  test.skip(info.project.name !== "chromium", "Tab focus differs on iOS WebKit");
  await signInAs(context, ORIGIN);
  await page.goto(`/en/reviewer/reports/${id(27)}`);
  const status = page.locator("[data-slot=status-actions]");

  await status.getByLabel("Action").selectOption("close");
  await status.getByRole("button", { name: "Apply change" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  await expect(status.getByRole("button", { name: "Apply change" })).toBeFocused();

  await page.goto(FULL);
  await expect(page.getByRole("heading", { level: 1, name: "Report" })).toBeVisible();
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});
