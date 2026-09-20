import { expect, test } from "@playwright/test";

test("the landing states the purpose, trust promise, and next action, using real API data only", async ({
  page
}) => {
  await page.goto("/en");

  await expect(page.getByRole("heading", { level: 1 })).toContainText("backed by sources");
  await expect(page.getByRole("search")).toBeVisible();
  await expect(page.getByRole("link", { name: "Browse project records" })).toHaveAttribute(
    "href",
    "/en/projects"
  );
  await expect(
    page.getByRole("link", { name: "Report a concern privately" }).first()
  ).toBeVisible();

  // The latest record is the newest one the API returned, with its real dates and status wording.
  const latest = page.locator("[data-slot=latest-record]");
  await expect(latest.getByRole("link", { name: "Synthetic example project 01" })).toBeVisible();
  await expect(latest.getByText("Recorded status")).toBeVisible();
  await expect(latest.locator("time")).toHaveAttribute("datetime", /^\d{4}-\d{2}-\d{2}$/);

  await expect(
    page.getByRole("heading", { level: 2, name: "How you can check what you read" })
  ).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "How ShaidaGo works" })).toBeVisible();
  await expect(page.getByText(/not an emergency service/i).first()).toBeVisible();
});

test("locality and category entry points come from the API, and open the directory already filtered", async ({
  page
}) => {
  await page.goto("/en");

  const localities = page.getByRole("region", { name: "Choose where to look" });
  await expect(localities.getByRole("link")).toHaveCount(3);
  await localities.getByRole("link", { name: "Synthetic Area Council B" }).click();
  await expect(page).toHaveURL(/\/en\/projects\?locality=bwari#results$/);
  await expect(
    page
      .getByRole("navigation", { name: "Active filters" })
      .getByRole("link", { name: "Remove filter: Synthetic Area Council B" })
  ).toBeVisible();

  await page.goto("/en");
  const categories = page.getByRole("region", { name: "Browse by category" });
  // Only categories that have records are offered.
  await expect(categories.getByRole("link")).toHaveCount(5);
  await categories.getByRole("link", { name: "Health" }).click();
  await expect(page).toHaveURL(/category=health/);
});

test("searching from the landing goes to the directory with the words as a shareable filter", async ({
  page
}) => {
  await page.goto("/en");
  await page.getByRole("searchbox", { name: "Search project records" }).fill("  project   07 ");
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page).toHaveURL(/\/en\/projects\?q=project\+07#results$/);
  await expect(page.locator("[data-slot=project-card]")).toHaveCount(1);
});

test("the landing works with JavaScript disabled, including search and every entry point", async ({
  browser
}) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  await page.goto("http://127.0.0.1:3100/en");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator("[data-slot=latest-record]").getByRole("link")).toBeVisible();
  await page.getByRole("searchbox", { name: "Search project records" }).fill("example");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/\/en\/projects\?q=example#results$/);
  await expect(page.locator("[data-slot=project-card]").first()).toBeVisible();
  await context.close();
});

test("the page makes no unsupported claim: no invented counts, partners, or testimonials", async ({
  page
}) => {
  await page.goto("/en");
  const text = (await page.locator("main").innerText()).toLowerCase();

  expect(text).not.toMatch(/\d+\s+(projects|communities|residents|reports|people|users)\b/);
  for (const word of ["testimonial", "partner", "trusted by", "award", "guarantee"]) {
    expect(text, word).not.toContain(word);
  }
});

test("keyboard users reach the skip link first and can jump to the main content", async ({
  page,
  browserName
}) => {
  // iOS WebKit does not Tab to links unless Full Keyboard Access is on; Tab order is proven in the
  // component suite and in Chromium here.
  test.skip(browserName === "webkit", "iOS WebKit does not Tab to links by default");
  await page.goto("/en");
  await page.keyboard.press("Tab");

  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  expect(await page.evaluate(() => document.activeElement?.id)).toBe("main-content");
});
