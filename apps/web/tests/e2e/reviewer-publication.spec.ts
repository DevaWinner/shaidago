import { expect, test, type Page, type TestInfo } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const id = (n: number) => `0198f1a2-7b3c-4d4e-8f5a-${String(n).padStart(12, "0")}`;

// Reports 4, 10, 16, 22, 28, 34, and 40 are "verified for a public update" in the mock. The two
// browser projects run in parallel against one mock, so each takes its own report per test.
const verified = (info: TestInfo, chromium: number, webkit: number): string =>
  `/en/reviewer/reports/${id(info.project.name === "chromium" ? chromium : webkit)}`;

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

const composer = (page: Page) => page.locator("[data-slot=publication-composer]");
const unique = (label: string, info: TestInfo) => `${label} ${info.project.name} ${Date.now()}`;

async function preview(page: Page, statement: string): Promise<void> {
  await page.getByLabel(/^Public statement/).fill(statement);
  await page.getByLabel(/^Date this applies from/).fill("2026-09-01");
  await page.getByRole("checkbox").first().check();
  await page.getByRole("button", { name: "Create a preview" }).click();
  await expect(page.getByRole("heading", { name: "Exact preview" })).toBeVisible();
}

test("the composer starts empty, offers only approved citations, and needs a verified report", async ({
  page
}, info) => {
  await page.goto(verified(info, 4, 4));
  await expect(page.getByLabel(/^Public statement/)).toHaveValue("");
  await expect(composer(page).getByRole("checkbox")).toHaveCount(2);
  await expect(composer(page)).toContainText("copied exactly from the approved source");

  await page.goto(`/en/reviewer/reports/${id(1)}`);
  await expect(page.locator("[data-slot=publication-blocked]")).toContainText(
    "Verified for a public update"
  );
  await expect(page.getByRole("button", { name: "Create a preview" })).toHaveCount(0);
});

test("a preview is drawn like the public timeline, nothing is public until confirmed, and publishing shows it there", async ({
  page
}, info) => {
  const text = unique("Fictional works were recorded as planned", info);
  const urls: string[] = [];

  page.on("request", (request) => urls.push(`${request.method()} ${request.url()}`));
  await page.goto(verified(info, 28, 34));
  await preview(page, text);

  const frame = page.locator("[data-slot=public-preview-frame]");

  await expect(frame.locator("[data-slot=timeline-item]")).toContainText(text);
  await expect(frame.locator("[data-slot=citation-entry]")).toHaveCount(1);
  await expect(page.getByText("Nothing is public yet.")).toBeVisible();
  expect(urls.some((url) => /:publish|\/publish/.test(url))).toBe(false);
  const publicBefore = await (await page.request.get("/en/projects/synthetic-project-20")).text();

  expect(publicBefore).not.toContain(text);

  await page.getByRole("button", { name: "Publish this update" }).click();
  await expect(page.getByRole("alertdialog")).toContainText("exactly as shown in the preview");
  expect(urls.some((url) => /\/publish/.test(url))).toBe(false);
  await page.getByRole("alertdialog").getByRole("button", { name: "Publish" }).click();
  await expect(page.locator("[data-slot=publication-published]")).toContainText("Published");

  await page.getByRole("link", { name: "See it on the public record" }).click();
  await expect(page).toHaveURL(/\/en\/projects\/synthetic-project-20$/);
  const entry = page.locator("[data-slot=timeline-item]").filter({ hasText: text });

  await expect(entry).toBeVisible();
  await expect(entry).toHaveAttribute("data-origin", "official");
  await expect(entry).toContainText("Confirmed by an official source");
});

test("text the API flags cannot be published, and no publish request is made", async ({
  page
}, info) => {
  const urls: string[] = [];

  page.on("request", (request) => urls.push(request.url()));
  await page.goto(verified(info, 10, 40));
  await preview(page, unique("This was corrupt work", info));

  await expect(page.locator("[data-slot=publication-preview] [role=alert]")).toContainText(
    "no cited passage contains it"
  );
  // The button is marked unavailable; a forced click must still open nothing and send nothing.
  await page.getByRole("button", { name: "Publish this update" }).click({ force: true });
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  expect(urls.some((url) => url.includes("/publish"))).toBe(false);
});

test("a preview that went stale is refused, nothing is published, and editing resumes", async ({
  page
}, info) => {
  const text = unique("Fictional stale statement", info);
  const path = verified(info, 16, 22);
  const reportId = path.split("/").pop() ?? "";

  await page.goto(path);
  await preview(page, text);
  const version = Number(
    (await page.locator("[data-slot=publication-preview]").innerText()).match(/version (\d+)/)?.[1]
  );

  // Someone else changes the report after the preview was made.
  const change = await page.request.post(`/api/reviewer/reports/${reportId}/status-transition`, {
    data: {
      command: "resume_review",
      expected_status: "verified_for_public_update",
      expected_version: version
    },
    headers: { Origin: ORIGIN }
  });

  expect(change.ok()).toBe(true);
  await page.getByRole("button", { name: "Publish this update" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Publish" }).click();

  await expect(page.locator("[data-section=publication]")).toContainText(
    "changed after it was made, so it was not published"
  );
  // The report is no longer verified, so the composer now says a status change comes first.
  await expect(page.locator("[data-slot=publication-blocked]")).toContainText(
    "Verified for a public update"
  );
  expect(await (await page.request.get("/en/projects/synthetic-project-20")).text()).not.toContain(
    text
  );
});

test("an earlier draft can be reopened and discarded, each on request", async ({ page }, info) => {
  const text = unique("Fictional draft to discard", info);

  await page.goto(verified(info, 4, 34));
  await preview(page, text);
  await page.reload();
  const drafts = page.locator("[data-slot=publication-drafts]");

  await expect(drafts).toContainText("State: Draft");
  await drafts.getByRole("button", { name: "Open preview" }).first().click();
  await expect(page.getByRole("heading", { name: "Exact preview" })).toBeVisible();
  await page.getByRole("button", { name: "Discard this draft" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Discard draft" }).click();
  await expect(page.getByText("The draft was discarded. Nothing was published.")).toBeVisible();
  await expect(page.locator("[data-slot=publication-drafts]")).toContainText("State: Withdrawn");
});

test("a phone-width composer and preview do not scroll sideways", async ({ page }, info) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.goto(verified(info, 4, 4));
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true
  );
});
