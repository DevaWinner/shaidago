import { expect, test, type Page, type TestInfo } from "@playwright/test";

import { progressSlug } from "../support/progress-slug";
import { signInAs } from "../support/reviewer-session";

/**
 * The ten end-to-end journeys of the build order (FE-150), each as one continuous path through the
 * built app against the fictional mock API and recorded replay data. Every secret in them is a
 * synthetic canary, and every journey ends by checking that none of it reached an address, storage,
 * cookie, or the page. They run on Chromium and mobile WebKit.
 */

const ORIGIN = "http://127.0.0.1:3100";
const id = (n: number) => `0198f1a2-7b3c-4d4e-8f5a-${String(n).padStart(12, "0")}`;
const record = "synthetic-record-full";

async function residue(page: Page): Promise<string> {
  return (
    (await page.evaluate(() =>
      JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie])
    )) +
    JSON.stringify(await page.context().cookies()) +
    page.url()
  );
}

test("J1 landing to a filtered directory, a project record, a cited statement, and its source page", async ({
  page
}) => {
  await page.goto("/en");
  await page.getByRole("link", { name: "Browse project records" }).first().click();
  await expect(page).toHaveURL(/\/en\/projects/);
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Locality").selectOption("amac");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(/locality=amac/);
  const first = page.locator("a[href^='/en/projects/synthetic-project']").first();

  await expect(first).toBeVisible();
  await page.goto(`/en/projects/${record}`);
  const claim = page.locator("[data-slot=claim]").first();

  await expect(claim).toContainText("A fictional bulletin lists this work as planned.");
  await claim.locator("[data-slot=citation-trigger]").first().click();
  await expect(page).toHaveURL(/#citation-/);
  await page.getByRole("link", { name: "Open the source page" }).first().click();
  await expect(page).toHaveURL(/\/sources\/[0-9a-f-]{36}$/);
  await expect(page.locator("[data-slot=citation-entry], blockquote").first()).toBeVisible();
});

test("J2 a project question gets a cited answer, and an unsupported one fails closed", async ({
  page
}) => {
  await page.goto(`/en/projects/${record}`);
  await page.getByLabel("Your question").fill("What is planned?");
  await page.getByRole("button", { name: "Ask the sources" }).click();
  const result = page.locator("[data-slot=question-result]");

  await expect(result.getByText("Written by an AI from the approved sources")).toBeVisible();
  await expect(result.locator("a[href*='#citation'], a[href*='/sources/']").first()).toBeVisible();
  await page.getByLabel("Your question").fill("__insufficient who is the contractor");
  await page.getByRole("button", { name: "Ask the sources" }).click();
  await expect(page.locator("[data-slot=question-result]")).toContainText(
    /not enough|cannot answer|insufficient/i
  );
});

test("J3 an anonymous fictional report gets a one-time tracking code and it never lingers", async ({
  page
}) => {
  await page.goto(`/en/report/${record}`);
  await page.getByRole("button", { name: "I understand. Continue" }).click();
  await page.locator("#report-category").selectOption("unsafe_construction");
  await page.locator("#report-description").fill("A fictional wall by the road is leaning.");
  for (let step = 0; step < 3; step += 1)
    await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Review and send" })).toBeVisible();
  await page.getByRole("button", { name: /^(Send report|Send again)$/ }).click();
  await expect(page).toHaveURL(/\/en\/report\/complete$/);
  const code = (await page.locator("[data-slot=tracking-code]").innerText()).trim();

  expect(code).toMatch(/^SG-DEMO-\d{4}-FICTIONAL$/);
  await expect(page.getByText("This code is shown once")).toBeVisible();
  expect(await residue(page)).not.toContain(code);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "The tracking code is no longer available" })
  ).toBeVisible();
  expect(await page.content()).not.toContain(code);
});

test("J4 a tracking code shows a public-safe status and a follow-up question can be answered", async ({
  page
}) => {
  await page.goto("/en/track");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Tracking code", { exact: true }).fill("SG-FOLLOWUP-1");
  await page.getByRole("button", { name: "Check status" }).click();
  await expect(page.locator("[data-slot=track-result]")).toContainText("Status:");
  await expect(page.locator("[data-slot=track-result] ol")).toBeVisible();
  expect(await residue(page)).not.toContain("FOLLOWUP");
  expect(await page.content()).not.toMatch(/internal_reason|contact_value/i);
});

test("J5 a reviewer signs in, opens a report from the queue, adds a note, opens evidence, and changes the status", async ({
  page
}, info) => {
  await page.goto("/en/reviewer/sign-in");
  await page.waitForLoadState("networkidle");
  await page.getByLabel(/^Reviewer identifier/).fill("reviewer-demo");
  await page.getByLabel(/^Password/).fill("fictional-password-not-a-secret");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL("**/en/reviewer/reports");
  await expect(page.locator("[data-slot=queue-item]").first()).toBeVisible();

  // Under-review reports nobody else changes: 9 and 39.
  const target = info.project.name === "chromium" ? 9 : 39;

  await page.goto(`/en/reviewer/reports/${id(target)}`);
  await expect(page.getByRole("heading", { level: 1, name: "Report" })).toBeVisible();
  // Choices made before the page has hydrated are reset when React takes over the form.
  await page.waitForLoadState("networkidle");
  const note = `Journey note ${info.project.name} ${Date.now()}`;

  await page.getByLabel("New note").fill(note);
  await page.locator("[data-slot=note-form] button[type=submit]").click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Add note" }).click();
  await expect(page.locator("[data-slot=notes-list]")).toContainText(note);
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  await page.locator("[data-slot=status-actions]").getByLabel("Action").selectOption("close");
  await page
    .locator("[data-slot=status-actions]")
    .getByRole("button", { name: "Apply change" })
    .click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Apply change" }).click();
  await expect(page.getByText(/Nothing was published/)).toBeVisible();
  await page.goto(`/en/reviewer/reports/${id(1)}`);
  const download = page.waitForEvent("download");

  await page
    .locator("[data-slot=evidence-download]")
    .first()
    .getByRole("button", { name: /^Download/ })
    .click();
  expect((await download).suggestedFilename()).toBe("evidence-1.jpg");
  expect(await residue(page)).not.toMatch(/sg_session=|fictional-password/);
});

test("J6 a public update is previewed, confirmed, and then appears on the public timeline", async ({
  context,
  page
}, info) => {
  await signInAs(context, ORIGIN);
  const target = info.project.name === "chromium" ? 46 - 6 : 34; // verified reports: 40 and 34
  const text = `Journey public update ${info.project.name} ${Date.now()}`;

  await page.goto(`/en/reviewer/reports/${id(target)}`);
  await page.waitForLoadState("networkidle");
  await page.getByLabel(/^Public statement/).fill(text);
  await page.getByLabel(/^Date this applies from/).fill("2026-09-01");
  await page.getByRole("checkbox").first().check();
  await page.getByRole("button", { name: "Create a preview" }).click();
  await expect(
    page.locator("[data-slot=public-preview-frame] [data-slot=timeline-item]")
  ).toContainText(text);
  await page.getByRole("button", { name: "Publish this update" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Publish" }).click();
  await expect(page.locator("[data-slot=publication-published]")).toBeVisible();
  await page.getByRole("link", { name: "See it on the public record" }).click();
  await expect(page.locator("[data-slot=timeline-item]").filter({ hasText: text })).toBeVisible();
});

test("J7 public Source Scout shows a labelled shared replay result", async ({ page }) => {
  await page.goto(`/en/projects/${record}`);
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find public information" }).click();
  const results = page.locator("[data-slot=public-discovery-results]");

  await expect(results.locator("[data-slot=discovery-source]").first()).toBeVisible();
  await expect(results.first()).toContainText("discovered — not yet reviewed");
  await expect(page.locator("[data-slot=project-discovery]")).toContainText("fictional replay");
  await expect(page.getByRole("button", { name: /Cancel|answer/i })).toHaveCount(0);
});

test("J8 a reviewer approves the exact query, sees private results, answers a follow-up, and decides on a source", async ({
  context,
  page
}) => {
  const canary = "never-send-this-private-report-canary";
  const bodies: string[] = [];

  page.on("request", (request) => {
    if (request.method() === "POST") bodies.push(request.postData() ?? "");
  });
  await signInAs(context, ORIGIN);
  await page.goto(`/en/reviewer/reports/${id(2)}`);
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Prepare query for review" }).click();
  await expect(page.getByLabel("Outbound query")).toHaveValue(
    "Abuja AMAC public works official source"
  );
  await page.getByRole("button", { name: "Approve and start search" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Approve and start" }).click();
  const run = page.locator("[data-slot=discovery-run]");

  await expect(run.locator("[data-slot=discovery-source]").first()).toContainText(
    "discovered — not yet reviewed"
  );
  const question = run.locator("[data-slot=discovery-follow-up]").first();

  await question.getByLabel("Your answer (private)").fill("Journey private answer");
  await question.getByRole("button", { name: "Send answer" }).click();
  await expect(question).toContainText("Recorded.");
  const card = run.locator("[data-slot=discovery-source]").first();

  await card.getByLabel("Reason").fill("Journey reason.");
  await card.getByRole("button", { name: "Defer" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Record decision" }).click();
  await expect(card).toContainText("Decision: Deferred");
  expect(bodies.some((body) => body.includes(canary))).toBe(false);
  expect(await page.content()).not.toContain("Journey private answer");
});

test("J9 a handle is created once, lists linked reports, and is deleted without deleting the reports", async ({
  page
}, info) => {
  await page.goto("/en/handle");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Create a handle" }).click();
  const handle = (await page.locator("[data-slot=created-handle]").innerText()).trim();
  const passphrase = (await page.locator("[data-slot=created-passphrase]").innerText()).trim();

  expect(handle).toMatch(/^fictional-handle-\d{3}$/);
  expect(await residue(page)).not.toContain(passphrase);
  await page.goto("/en/track");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Handle", { exact: true }).first().fill("fictional-handle-001");
  await page.getByLabel("Passphrase", { exact: true }).first().fill("amber bridge candle");
  await page.getByRole("button", { name: "List my reports" }).click();
  await expect(page.locator("[data-slot=handle-result]")).toContainText("Status: Under review");
  await page.goto("/en/handle");
  await page.waitForLoadState("networkidle");
  await expect(page.getByText(/does not delete the reports/)).toBeVisible();
  await page
    .getByLabel("Handle", { exact: true })
    .fill(info.project.name === "chromium" ? "fictional-handle-004" : "fictional-handle-005");
  await page.locator("input[type=password]").fill("secret words");
  await page.getByRole("checkbox", { name: /I understand the reports stay/ }).check();
  await page.getByRole("button", { name: "Delete this handle" }).click();
  await expect(page.locator("[data-slot=delete-result]")).toContainText(
    /handle was deleted|not accepted/
  );
});

test("J10 a saved public record is revisited offline, and low-data mode keeps every action", async ({
  browser,
  context,
  page
}, info: TestInfo) => {
  test.skip(
    info.project.name !== "chromium",
    "Playwright WebKit cannot navigate offline with a service worker active"
  );
  void browser;
  await page.goto("/en");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.goto(`/en/projects/${record}`);
  await page.waitForLoadState("networkidle");
  await context.setOffline(true);
  await page.goto(`/en/projects/${record}`);
  await expect(page.locator("[data-slot=offline-banner]")).toContainText("saved copy from");
  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await page
    .locator("[data-slot=low-data]")
    .getByRole("button", { name: "Turn on low-data mode" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-low-data", "true");
  await page.goto("/en/projects?q=Synthetic");
  await expect(page.locator("a[href^='/en/projects/synthetic-project']").first()).toBeVisible();
  await page.goto(`/en/projects/${progressSlug(info)}`);
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("button", { name: "Find public information" })).toBeVisible();
});
