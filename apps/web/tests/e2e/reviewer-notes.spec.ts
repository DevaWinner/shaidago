import { expect, test } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const id = (n: number) => `0198f1a2-7b3c-4d4e-8f5a-${String(n).padStart(12, "0")}`;
const FULL = `/en/reviewer/reports/${id(1)}`;

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

const unique = (label: string, testInfo: { project: { name: string } }) =>
  `${label} ${testInfo.project.name} ${Date.now()}`;

test("notes are private plain text, oldest first, with later pages one link away", async ({
  page
}) => {
  await page.goto(FULL);
  const list = page.locator("[data-slot=notes-list] > li");

  await expect(list).toHaveCount(20);
  await expect(list.first()).toContainText("Seeded fictional note 1.");
  await expect(list.nth(1)).toContainText("Seeded note with <b>markup</b> that must stay text.");
  expect(await list.nth(1).locator("b").count()).toBe(0);
  await page.getByRole("link", { name: "Show later notes" }).click();
  await expect(page).toHaveURL(/notes=/);
  await expect(list).toHaveCount(2);
  await page.getByRole("link", { name: "Back to the first notes" }).click();
  await expect(list).toHaveCount(20);
});

test("adding a note needs confirmation, then appears and clears the box", async ({
  page
}, testInfo) => {
  const text = unique("Fictional private note", testInfo);
  const posts: string[] = [];

  page.on("request", (request) => {
    if (request.method() === "POST") posts.push(request.url());
  });
  await page.goto(`/en/reviewer/reports/${id(3)}`);
  await page.getByLabel("New note").fill(text);
  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Keep editing" }).click();
  expect(posts).toEqual([]);
  await expect(page.getByLabel("New note")).toHaveValue(text);

  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Add note" }).click();
  await expect(page.getByText("Note added.")).toBeVisible();
  await expect(page.locator("[data-slot=notes-list]")).toContainText(text);
  await expect(page.getByLabel("New note")).toHaveValue("");
  expect(posts).toHaveLength(1);
  expect(posts[0]).toContain(`/api/reviewer/reports/${id(3)}/notes`);
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).toBe(
    "{}"
  );
});

test("markup and an outage are refused clearly and the text stays", async ({ page }) => {
  await page.goto(`/en/reviewer/reports/${id(3)}`);
  await page.getByLabel("New note").fill("<b>markup</b>");
  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Add note" }).click();
  await expect(page.locator("[data-section=notes] [role=alert]")).toContainText(
    "Remove formatting or markup"
  );
  await expect(page.getByLabel("New note")).toHaveValue("<b>markup</b>");

  await page.getByLabel("New note").fill("zz-fail please");
  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Add note" }).click();
  await expect(page.locator("[data-section=notes] [role=alert]")).toContainText("unavailable");
  await expect(page.getByLabel("New note")).toHaveValue("zz-fail please");
});

test("a cross-origin note is refused by the boundary and nothing reaches the notes", async ({
  request
}) => {
  const response = await request.post(`/api/reviewer/reports/${id(3)}/notes`, {
    data: { body: "cross-site note" },
    headers: { Origin: "http://evil.example" }
  });

  expect(response.status()).toBe(403);
  expect(response.headers()["cache-control"]).toContain("no-store");
});

test("evidence is downloaded only on request, freshly each time, and never shown inline", async ({
  page
}) => {
  const requests: string[] = [];

  page.on("request", (request) => {
    if (request.url().includes("/evidence/")) requests.push(request.url());
  });
  await page.goto(FULL);
  await page.waitForTimeout(400);
  expect(requests).toEqual([]);

  const first = page.locator("[data-slot=evidence-download]").first();
  const download = page.waitForEvent("download");

  await first.getByRole("button", { name: "Download evidence-1.jpg" }).click();
  expect((await download).suggestedFilename()).toBe("evidence-1.jpg");
  await expect(first).toContainText("The download of evidence-1.jpg started.");
  const again = page.waitForEvent("download");

  await first.getByRole("button", { name: "Download evidence-1.jpg" }).click();
  await again;
  expect(requests).toHaveLength(2);
  expect(await page.locator("img, iframe, embed, object").count()).toBe(0);
});

test("a failed or expired download says so, offers sign-in, and keeps the page", async ({
  page
}) => {
  await page.route("**/api/reviewer/reports/*/evidence/*", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/problem+json",
      body: JSON.stringify({ code: "unauthenticated", status: 401 })
    })
  );
  await page.goto(FULL);
  const first = page.locator("[data-slot=evidence-download]").first();

  await first.getByRole("button", { name: "Download evidence-1.jpg" }).click();
  await expect(first).toContainText("Your session ended");
  await expect(first.getByRole("link", { name: "Sign in again" })).toHaveAttribute(
    "href",
    /reason=expired&next=/
  );
});

test("a question can be asked and withdrawn, each after confirmation", async ({
  page
}, testInfo) => {
  const text = unique("Fictional question about the gate", testInfo);

  await page.goto(`/en/reviewer/reports/${id(2)}`);
  await page.getByLabel("New question for the reporter").fill(text);
  await page.getByRole("button", { name: "Ask question" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Send question" }).click();
  const item = page.locator("[data-slot=question-list] > li").filter({ hasText: text });

  await expect(item).toBeVisible();
  await item.getByRole("button", { name: /^Withdraw the question/ }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Withdraw question" }).click();
  await expect(item).toContainText("Withdrawn");
  await expect(item.getByRole("button")).toHaveCount(0);
});
