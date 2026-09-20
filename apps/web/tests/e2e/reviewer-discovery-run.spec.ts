import { expect, test, type Page } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000002";
const PUBLIC_RUN = "00000000-0000-4000-8000-000000000801";

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

const run = (page: Page) => page.locator("[data-slot=discovery-run]");

/** Prepares the query (optionally with a scenario switch as the public term), approves it, and returns the run id. */
async function start(page: Page, scenario = ""): Promise<string> {
  await page.goto(`/en/reviewer/reports/${REPORT}`);
  // Typing before the page has hydrated is lost when React takes over the field.
  await page.waitForLoadState("networkidle");
  if (scenario !== "") {
    await page.getByLabel("Optional public search terms").fill(scenario);
    await expect(page.getByLabel("Optional public search terms")).toHaveValue(scenario);
  }
  await page.getByRole("button", { name: "Prepare query for review" }).click();
  await expect(page.getByLabel("Outbound query")).toBeVisible();
  await page.getByRole("button", { name: "Approve and start search" }).click();
  const created = page.waitForResponse(
    (response) => /\/discovery$/.test(response.url()) && response.request().method() === "POST"
  );

  await page.getByRole("alertdialog").getByRole("button", { name: "Approve and start" }).click();
  const body = (await (await created).json()) as { run_id: string };

  return body.run_id;
}

test("every result is labelled unreviewed, repeats are grouped, an instruction page is flagged, and an unsafe link is not made", async ({
  page
}) => {
  await start(page);
  await expect(run(page).locator("[data-slot=discovery-source]")).toHaveCount(3);
  for (const card of await run(page).locator("[data-slot=discovery-source]").all()) {
    await expect(card).toContainText("discovered — not yet reviewed");
  }
  await expect(
    run(page).locator("[data-slot=discovery-duplicates] [data-slot=discovery-source]")
  ).toHaveCount(1);
  await expect(run(page)).toContainText("tries to give instructions");
  await expect(run(page)).toContainText("could not be shown safely");
  expect(await page.locator("a[href^='javascript']").count()).toBe(0);
  await expect(run(page)).toContainText("Publication date unknown");
  await expect(run(page)).toContainText("The pages disagree about this date.");
  const link = run(page).getByRole("link", { name: "Open the original page (new tab)" }).first();

  await expect(link).toHaveAttribute("target", "_blank");
  await expect(link).toHaveAttribute("rel", /noopener/);
});

test("analysis is separate from the sources, cites cards of this run, and shows no score", async ({
  page
}) => {
  await start(page);
  const analysis = run(page).locator("[data-slot=discovery-analysis]");

  await expect(analysis).toContainText("an explanation, not a source");
  await expect(analysis.locator("[data-section=facts]")).toContainText("public works update");
  await expect(analysis.locator("[data-section=claims]")).toContainText("example.test says:");
  await expect(analysis.locator("[data-section=contradictions]")).toContainText(
    "different fictional dates"
  );
  await expect(analysis.locator("[data-section=gaps]")).toContainText("No completion date");
  await expect(analysis.locator("[data-section=safety]")).toContainText("human review");
  await analysis.locator("[data-section=facts] a").first().click();
  await expect(page).toHaveURL(/#source-/);
  expect(await run(page).innerText()).not.toMatch(/confidence: |score:|\d+ ?%/i);
});

test("an analysis that cannot be checked shows no analysis, and the ten-source cap holds", async ({
  page
}) => {
  await start(page, "zz-invalid");
  await expect(run(page)).toContainText("No analysis is shown");
  await expect(run(page).locator("[data-slot=discovery-analysis]")).toHaveCount(0);
  await expect(run(page).locator("[data-slot=discovery-source]")).toHaveCount(3);

  await start(page, "zz-cap");
  await expect(run(page).locator("[data-slot=discovery-source]")).toHaveCount(10);
});

test("progress uses the real stage and counts, then polling stops for good", async ({ page }) => {
  const reads: string[] = [];

  page.on("request", (request) => {
    if (/\/api\/reviewer\/discovery\/[0-9a-f-]{36}/.test(request.url())) reads.push(request.url());
  });
  await start(page, "zz-progress");
  await expect(run(page)).toHaveAttribute("data-status", "searching");
  await expect(run(page)).toContainText("Found 0, read 0, analysed 0.");
  expect(await run(page).locator("progress, [role=progressbar]").count()).toBe(0);
  await expect(run(page)).toHaveAttribute("data-status", "analysing", { timeout: 8000 });
  await expect(run(page)).toHaveAttribute("data-status", "complete", { timeout: 12000 });
  const settled = reads.length;

  await page.waitForTimeout(3500);
  expect(reads.length).toBe(settled);
});

test("cancelling needs confirmation and keeps what was already found", async ({ page }) => {
  await start(page, "zz-queued");
  await expect(run(page)).toHaveAttribute("data-status", "queued");
  await run(page).getByRole("button", { name: "Cancel this run" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Keep it running" }).click();
  await expect(run(page)).toHaveAttribute("data-status", "queued");
  await run(page).getByRole("button", { name: "Cancel this run" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Cancel the run" }).click();
  await expect(run(page)).toHaveAttribute("data-status", "cancelled");
  await expect(run(page)).toContainText(
    "Cancelled. Anything found before cancelling is shown below and is incomplete."
  );
  await expect(run(page).locator("[data-slot=discovery-source]")).toHaveCount(1);
  await expect(run(page).getByRole("button", { name: "Cancel this run" })).toHaveCount(0);
});

test("a failed run and an outage each say what happened, and the outage can be retried", async ({
  page
}) => {
  await start(page, "zz-failed");
  await expect(run(page)).toContainText("The search provider was unavailable.");
  await expect(run(page)).toContainText("Nothing was found before it stopped.");

  await start(page, "zz-down");
  await expect(run(page).getByRole("alert")).toBeVisible();
  await run(page).getByRole("button", { name: "Check again" }).click();
  await expect(run(page).locator("[data-slot=discovery-source]").first()).toBeVisible();
});

test("going offline keeps the results on screen and says so", async ({ context, page }) => {
  await start(page);
  await expect(run(page).locator("[data-slot=discovery-source]").first()).toBeVisible();
  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await expect(run(page)).toContainText("You are offline");
  await expect(run(page).locator("[data-slot=discovery-source]").first()).toBeVisible();
  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(run(page)).not.toContainText("You are offline");
});

test("a follow-up answer is sent once in a POST body and never appears in the address, storage, or page afterwards", async ({
  page
}) => {
  const canary = "PRIVATE-ANSWER-CANARY-7731";
  const seen: { url: string; body: string }[] = [];
  const messages: string[] = [];

  page.on("request", (request) =>
    seen.push({ url: request.url(), body: request.postData() ?? "" })
  );
  page.on("console", (message) => messages.push(message.text()));
  await start(page);
  const first = run(page).locator("[data-slot=discovery-follow-up]").first();

  await first.getByLabel("Your answer (private)").fill(canary);
  await first.getByRole("button", { name: "Send answer" }).click();
  await expect(first).toContainText("Recorded. What you typed is not shown again.");

  expect(seen.filter((item) => item.url.includes(canary))).toEqual([]);
  expect(seen.filter((item) => item.body.includes(canary)).map((item) => item.url)).toEqual([
    expect.stringContaining("/follow-up-answers")
  ]);
  expect(page.url()).not.toContain(canary);
  expect(await page.content()).not.toContain(canary);
  expect(messages.join("\n")).not.toContain(canary);
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).toBe(
    "{}"
  );
  await expect(run(page).locator("[data-slot=discovery-follow-up]")).toHaveCount(2);
});

test("attaching a source needs a reason and confirmation and does not verify or publish anything", async ({
  page
}) => {
  await start(page);
  const card = run(page).locator("[data-slot=discovery-source]").first();

  await card.getByRole("button", { name: "Attach as a pending source" }).click();
  await expect(card).toContainText("Give a reason.");
  await card.getByLabel("Reason").fill("Matches the record.");
  await card.getByRole("button", { name: "Attach as a pending source" }).click();
  await expect(page.getByRole("alertdialog")).toContainText(
    "does not approve any fact or publish anything"
  );
  await page.getByRole("alertdialog").getByRole("button", { name: "Record decision" }).click();
  await expect(card).toContainText("Decision: Attached as a pending source (not verified)");
  await expect(card).toContainText("discovered — not yet reviewed");
  await expect(card.getByRole("button", { name: "Reconsider" })).toBeVisible();
  await expect(card.getByRole("button", { name: "Reject" })).toHaveCount(0);
});

test("approving or rejecting the run is confirmed and recorded", async ({ page }) => {
  await start(page);
  await expect(run(page)).toContainText("needs a reviewer's decision");
  await run(page).getByRole("button", { name: "Approve completion" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Record decision" }).click();
  await expect(run(page)).toHaveAttribute("data-status", "complete");
  await expect(run(page).getByRole("button", { name: "Approve completion" })).toHaveCount(0);
});

test("public and report-scoped runs cannot be read through each other's routes", async ({
  page,
  request
}) => {
  const id = await start(page);

  expect((await request.get(`/api/public/discovery/${id}`)).status()).toBe(404);
  const cross = await page.request.get(`/api/reviewer/discovery/${PUBLIC_RUN}`);

  expect(cross.status()).toBe(404);
  expect(cross.headers()["cache-control"]).toContain("no-store");
  const projectPage = await page.request.get("/en/projects/synthetic-record-full");

  expect(await projectPage.text()).not.toContain(id);
});

test("the private query and run state are not left in the address, history, or storage", async ({
  page
}) => {
  const id = await start(page);

  await expect(run(page)).toBeVisible();
  expect(page.url()).not.toContain(id);
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).toBe(
    "{}"
  );
  await page.reload();
  await expect(page.locator("[data-slot=discovery-run]")).toHaveCount(0);
});
