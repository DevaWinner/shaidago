import { expect, test } from "@playwright/test";

test("a resident starts a bounded public discovery replay without putting state in the address", async ({
  page
}) => {
  await page.goto("/en/projects/synthetic-record-full");
  const before = page.url();

  await page.getByRole("button", { name: "Find public information" }).click();

  await expect(page.getByText("Search completed").first()).toBeVisible();
  await expect(page.getByText("Found 3; fetched 3; analysed 2.")).toBeVisible();
  await expect(page.getByText("Showing a fictional replay for the demo.")).toBeVisible();
  expect(page.url()).toBe(before);
  expect(await page.locator("progress").count()).toBe(0);
  const html = (await page.content()).toLowerCase();
  for (const privateTerm of [
    "tracking_code",
    "contact_value",
    "reviewer_note",
    "internal_reason"
  ]) {
    expect(html).not.toContain(privateTerm);
  }
});

test("a resident is told when a public discovery run is unavailable", async ({ page }) => {
  await page.goto("/en/projects/synthetic-record-minimal");

  await page.getByRole("button", { name: "Find public information" }).click();

  await expect(page.getByText("A public search is not available right now.")).toBeVisible();
});
