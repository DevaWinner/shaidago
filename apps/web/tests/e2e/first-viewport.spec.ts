import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function box(page: Page, selector: string) {
  const found = await page.locator(selector).first().boundingBox();

  if (found === null) {
    throw new Error(`no box for ${selector}`);
  }

  return found;
}

test("the first viewport shows the record, its state and date, the primary action, and a secondary report action", async ({
  page
}) => {
  await page.goto("/");
  const height = page.viewportSize()?.height ?? 0;

  const wide = (page.viewportSize()?.width ?? 0) >= 1024;

  // Wide screens show the whole record field in the first viewport. Small screens show the title
  // and primary action first; the record follows, before its evidence rail.
  for (const selector of [
    "[data-slot=fv-title]",
    "[data-slot=fv-primary]",
    ...(wide ? ["[data-slot=fv-entry]"] : [])
  ]) {
    const { y, height: h } = await box(page, selector);
    expect(y, selector).toBeGreaterThanOrEqual(0);
    expect(y + Math.min(h, 40), selector).toBeLessThanOrEqual(height);
  }

  await expect(page.getByRole("heading", { level: 1 })).toContainText("AMAC and Bwari");
  await expect(page.getByText("Fictional example")).toBeVisible();
  await expect(page.getByText("Last checked").first()).toBeVisible();
  await expect(page.getByText("Awaiting verification").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Browse project records" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Report a concern privately" })).toBeVisible();
});

test("browse is the visually primary action and reporting is clearly secondary", async ({
  page
}) => {
  await page.goto("/");

  const styles = await page.evaluate(() => {
    const read = (selector: string) => {
      const style = getComputedStyle(document.querySelector(selector) as Element);

      return { background: style.backgroundColor, size: Number.parseFloat(style.fontSize) };
    };

    return {
      primary: read("[data-slot=fv-primary]"),
      secondary: read("[data-slot=fv-secondary] [data-slot=button]")
    };
  });

  expect(styles.primary.background).toBe("rgb(0, 110, 101)");
  expect(styles.secondary.background).toBe("rgb(255, 252, 246)");
  expect(styles.primary.size).toBeGreaterThan(styles.secondary.size);
});

test("the evidence rail sits beside the record on wide screens and after it on narrow ones", async ({
  page
}) => {
  await page.goto("/");
  const record = await box(page, "[data-slot=fv-record]");
  const rail = await box(page, "[data-slot=fv-rail]");
  const wide = (page.viewportSize()?.width ?? 0) >= 1024;

  if (wide) {
    expect(rail.x).toBeGreaterThan(record.x + record.width - 1);
    expect(Math.abs(rail.y - record.y)).toBeLessThan(40);
  } else {
    expect(rail.y).toBeGreaterThanOrEqual(record.y + record.height - 1);
    const primary = await box(page, "[data-slot=fv-primary]");
    expect(Math.abs(primary.width - record.width)).toBeLessThan(2);
  }
});

test("there is no horizontal scrolling and no automated accessibility violation", async ({
  page
}) => {
  await page.goto("/");

  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    )
  ).toBeLessThanOrEqual(0);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});

test("keyboard users reach the skip link first and can jump to the main content", async ({
  page,
  browserName
}) => {
  // iOS WebKit does not Tab to links unless Full Keyboard Access is on; Tab order is proven in the
  // component suite and in Chromium here.
  test.skip(browserName === "webkit", "iOS WebKit does not Tab to links by default");
  await page.goto("/");
  await page.keyboard.press("Tab");

  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  expect(await page.evaluate(() => document.activeElement?.id)).toBe("main-content");
});

test("the page works without JavaScript, including the citation link", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  await page.goto("http://127.0.0.1:3100/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.getByRole("link", { name: "Source 1" }).click();
  expect(page.url()).toContain("#citation-example-1");
  await context.close();
});

test("the landing document is public, static, and not marked private", async ({ request }) => {
  const response = await request.get("/");

  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"] ?? "").not.toContain("no-store");
  expect(await response.text()).toContain("Fictional example");
});
