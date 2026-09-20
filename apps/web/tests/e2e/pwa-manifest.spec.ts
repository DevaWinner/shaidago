import { expect, test } from "@playwright/test";

test("the manifest is served, linked from the page, and claims no unapproved icons", async ({
  page,
  request
}) => {
  const response = await request.get("/manifest.webmanifest");

  expect(response.status()).toBe(200);
  const manifest = (await response.json()) as Record<string, unknown>;

  expect(manifest["name"]).toBe("ShaidaGo");
  expect(manifest["start_url"]).toBe("/");
  expect(manifest["scope"]).toBe("/");
  expect(manifest["display"]).toBe("standalone");
  expect(manifest["theme_color"]).toBe("#F7F2E8");
  expect(manifest["icons"]).toBeUndefined();

  await page.goto("/en");
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute(
    "href",
    "/manifest.webmanifest"
  );
});

test("the start address resolves to a supported language without a stored identifier", async ({
  page
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/(en|ha|ig|yo)$/);
});
