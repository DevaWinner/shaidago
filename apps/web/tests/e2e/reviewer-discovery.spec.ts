import { expect, test } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000001";
const PRIVATE_CANARY = "never-send-this-private-report-canary";

test.beforeEach(async ({ context }) => {
  await signInAs(context, ORIGIN);
});

test("a reviewer approves the exact query before discovery starts and no private canary leaves the page", async ({
  page
}) => {
  const bodies: string[] = [];
  const urls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/reviewer/reports/")) {
      urls.push(request.url());
      bodies.push(request.postData() ?? "");
    }
  });
  await page.goto(`/en/reviewer/reports/${REPORT}`);
  await expect(page.locator("[data-slot=discovery-preview]")).toContainText(
    "does not receive report text"
  );
  await page.getByLabel("Optional public search terms").fill("public works");
  await page.getByRole("button", { name: "Prepare query for review" }).click();
  await expect(page.getByLabel("Outbound query")).toHaveValue(
    "Abuja AMAC public works official source"
  );
  await expect(page.locator("[data-slot=discovery-plan]")).toContainText("report description");
  await page.getByRole("button", { name: "Approve and start search" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Approve and start" }).click();
  await expect(page.locator("[data-slot=discovery-preview]")).toContainText(
    "Source search started"
  );
  expect(urls.every((url) => !url.includes(PRIVATE_CANARY))).toBe(true);
  expect(bodies.every((body) => !body.includes(PRIVATE_CANARY))).toBe(true);
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).toBe(
    "{}"
  );
});
