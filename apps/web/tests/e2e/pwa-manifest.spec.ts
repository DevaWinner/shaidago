import { expect, test } from "@playwright/test";

test("the manifest is served, linked from the page, and serves its evidence-search icons", async ({
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
  const icons = manifest["icons"] as { src: string; sizes: string; type: string }[];

  for (const icon of icons) {
    const file = await request.get(icon.src);

    expect(file.status(), icon.src).toBe(200);
    expect(file.headers()["content-type"]).toContain(icon.type);
  }
  const sizes = await Promise.all(
    icons
      .filter((icon) => icon.type === "image/png")
      .map(async (icon) => (await request.get(icon.src)).body())
  );

  for (const body of sizes) expect(body.subarray(1, 4).toString()).toBe("PNG");

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
