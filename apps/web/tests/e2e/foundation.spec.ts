import { expect, test } from "@playwright/test";

test("the foundation renders safe metadata without requesting an internal API", async ({
  page
}) => {
  const response = await page.goto("/");

  expect(response?.status()).toBe(200);
  await expect(page).toHaveTitle("ShaidaGo");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");

  const requestedURLs = await page.evaluate(() =>
    performance.getEntriesByType("resource").map((entry) => entry.name)
  );
  expect(requestedURLs.some((url) => url.includes("railway.internal"))).toBe(false);
});

test("an unknown route returns a generic unavailable response", async ({ page }) => {
  const response = await page.goto("/not-a-real-record");

  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "This page is not available" })).toBeVisible();
  await expect(page.getByText(/does not confirm whether a private record exists/i)).toBeVisible();
});
