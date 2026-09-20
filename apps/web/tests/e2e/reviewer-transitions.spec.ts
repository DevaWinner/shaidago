import { expect, test, type TestInfo } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const id = (n: number) => `0198f1a2-7b3c-4d4e-8f5a-${String(n).padStart(12, "0")}`;

// The two browser projects run in parallel against one mock, so each uses its own reports.
// Report n has status STATUSES[(n - 1) % 6]: 0 received, 1 needs_information, 2 under_review,
// 3 verified_for_public_update, 4 referred, 5 closed.
const report = (info: TestInfo, chromium: number, webkit: number): string =>
  `/en/reviewer/reports/${id(info.project.name === "chromium" ? chromium : webkit)}`;

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

const actions = (page: import("@playwright/test").Page) =>
  page.locator("[data-slot=status-actions]");
const confirm = (page: import("@playwright/test").Page) =>
  page.getByRole("alertdialog").getByRole("button", { name: "Apply change" });

test("only the commands the contract allows are offered, and none of them publishes", async ({
  page
}) => {
  await page.goto(`/en/reviewer/reports/${id(4)}`);
  const options = await actions(page).getByLabel("Action").locator("option").allTextContents();

  expect(options).toEqual(["Resume review", "Record a referral", "Close the report"]);
  await expect(actions(page)).toContainText("A status change never publishes text");
});

test("a status change is confirmed, applied, announced, and appears in the history", async ({
  page
}, info) => {
  const posts: { url: string; body: string }[] = [];

  page.on("request", (request) => {
    if (request.method() === "POST")
      posts.push({ url: request.url(), body: request.postData() ?? "" });
  });
  await page.goto(report(info, 13, 19));
  await expect(page.locator("[data-slot=report-header]")).toContainText("Status: Received");
  await actions(page).getByLabel("Action").selectOption("start_review");
  await actions(page).getByRole("button", { name: "Apply change" }).click();
  await expect(page.getByRole("alertdialog")).toContainText("does not publish anything");
  expect(posts).toEqual([]);
  await confirm(page).click();

  await expect(
    page.getByText("Status changed from Received to Under review. Nothing was published.")
  ).toBeVisible();
  await expect(page.locator("[data-slot=report-header]")).toContainText("Status: Under review");
  await expect(page.locator("[data-slot=history-list]")).toContainText(
    "From Received to Under review"
  );
  expect(posts).toHaveLength(1);
  expect(JSON.parse(posts[0]?.body ?? "{}")).toMatchObject({
    command: "start_review",
    expected_status: "received",
    expected_version: expect.any(Number)
  });
  expect(
    await page
      .locator("[data-slot=status-actions]")
      .getByLabel("Action")
      .locator("option")
      .allTextContents()
  ).toContain("Close the report");
});

test("a reporter message is shown to the reporter side of the history, and a reason stays private", async ({
  page
}, info) => {
  await page.goto(report(info, 15, 21));
  await actions(page).getByLabel("Action").selectOption("close");
  await actions(page)
    .getByLabel("Message the reporter will see")
    .fill("We have closed this fictional report.");
  await actions(page).getByLabel("Internal reason (private)").fill("Fictional closing reason.");
  await actions(page).getByRole("button", { name: "Apply change" }).click();
  await expect(page.getByRole("alertdialog")).toContainText("Check the message before you confirm");
  await confirm(page).click();

  const history = page.locator("[data-slot=history-list]");

  await expect(history).toContainText(
    "Shown to the reporter: We have closed this fictional report."
  );
  await expect(history).toContainText("Internal reason (private): Fictional closing reason.");
  await expect(page.locator("[data-slot=report-header]")).toContainText("Status: Closed");
});

test("reopening needs a reason before anything is sent", async ({ page }, info) => {
  await page.goto(report(info, 12, 18));
  await actions(page).getByRole("button", { name: "Apply change" }).click();
  await expect(actions(page)).toContainText("Give a reason for reopening.");
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
});

test("a stale view is refused with a calm explanation, the text is kept, and a reload recovers", async ({
  page
}, info) => {
  await page.goto(report(info, 25, 31));
  await actions(page).getByLabel("Internal reason (private)").fill("Typed before the conflict");
  await actions(page).getByRole("button", { name: "Apply change" }).click();
  await confirm(page).click();

  await expect(actions(page).getByRole("alert")).toContainText("changed while you were working");
  await expect(actions(page).getByLabel("Internal reason (private)")).toHaveValue(
    "Typed before the conflict"
  );
  await actions(page).getByRole("button", { name: "Reload the report" }).click();
  await expect(actions(page).getByRole("alert")).toHaveCount(0);
  await actions(page).getByRole("button", { name: "Apply change" }).click();
  await confirm(page).click();
  await expect(page.getByText(/Nothing was published/)).toBeVisible();
});

test("a status change reports published:false and never touches public updates", async ({
  page
}, info) => {
  const urls: string[] = [];

  page.on("request", (request) => urls.push(request.url()));
  await page.goto(report(info, 37, 43));
  await actions(page).getByRole("button", { name: "Apply change" }).click();
  const response = page.waitForResponse((item) => item.url().includes("/status-transition"));

  await confirm(page).click();
  const body = (await (await response).json()) as { published?: boolean };

  expect(body.published).toBe(false);
  await expect(page.getByText(/Nothing was published/)).toBeVisible();
  expect(urls.some((url) => url.includes("public-updates") || url.includes("/projects/"))).toBe(
    false
  );
});

test("the confirmation is keyboard reachable and returns focus to the page", async ({
  page
}, info) => {
  test.skip(info.project.name !== "chromium", "Tab focus differs on iOS WebKit");
  await page.goto(report(info, 27, 33));
  await actions(page).getByLabel("Action").selectOption("close");
  await actions(page).getByRole("button", { name: "Apply change" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("alertdialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  await expect(actions(page)).toBeVisible();
  expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe("BODY");
});
