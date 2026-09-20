import { progressSlug } from "../support/progress-slug";
import { expect, test } from "@playwright/test";

const LOCALES = ["en", "ha", "ig", "yo"] as const;
const toggle = (page: import("@playwright/test").Page) => page.locator("[data-slot=low-data]");

test("the switch sets one plain cookie, applies before paint after a reload, and can be turned off", async ({
  context,
  page
}) => {
  await page.goto("/en");
  await page.waitForLoadState("networkidle");
  await toggle(page).getByRole("button", { name: "Turn on low-data mode" }).click();
  await expect(toggle(page)).toContainText("Low-data mode is on");
  await expect(page.locator("html")).toHaveAttribute("data-low-data", "true");

  const cookie = (await context.cookies()).find((item) => item.name === "sg_low_data");

  expect(cookie?.value).toBe("1");
  expect(cookie?.httpOnly).toBe(false);
  expect(cookie?.sameSite).toBe("Lax");
  expect(cookie?.expires ?? 0).toBeGreaterThan(Date.now() / 1000 + 300 * 24 * 3600);

  // The attribute is present as soon as the document is parsed, before the app has hydrated.
  await page.route("**/_next/static/**", (route) => route.abort());
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("data-low-data", "true");
  await page.unroute("**/_next/static/**");

  await page.reload();
  await toggle(page).getByRole("button", { name: "Turn off low-data mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-low-data", "false");
  expect((await context.cookies()).find((item) => item.name === "sg_low_data")?.value).toBe("0");
});

test("in every language the mode removes motion but keeps every core action, without a layout break", async ({
  context,
  page,
  baseURL
}) => {
  await context.addCookies([
    { name: "sg_low_data", value: "1", url: baseURL ?? "http://127.0.0.1:3100" }
  ]);

  for (const locale of LOCALES) {
    await page.goto(`/${locale}`);
    await expect(page.locator("html")).toHaveAttribute("data-low-data", "true");
    const motion = await page.evaluate(() => {
      const style = getComputedStyle(document.querySelector("a") as Element);

      return { transition: style.transitionDuration, animation: style.animationName };
    });

    expect(motion.transition).toMatch(/^0s(, 0s)*$/);
    expect(motion.animation).toBe("none");
    await page.goto(`/${locale}/projects`);
    await expect(page.locator("form[role=search]")).toBeVisible();
    await expect(page.locator("[data-slot=project-card], article").first()).toBeVisible();
    await page.goto(`/${locale}/report`);
    await expect(page.locator("main")).toBeVisible();
    for (const width of [320, 1280]) {
      await page.setViewportSize({ width, height: 800 });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth
        )
      ).toBeLessThanOrEqual(0);
    }
  }
});

test("task completion is the same: a directory search and a public Source Scout run work in low-data mode", async ({
  context,
  page,
  baseURL
}) => {
  await context.addCookies([
    { name: "sg_low_data", value: "1", url: baseURL ?? "http://127.0.0.1:3100" }
  ]);
  await page.goto("/en/projects?q=Synthetic");
  await expect(page.locator("a[href^='/en/projects/synthetic-project']").first()).toBeVisible();
  await page.goto("/en/projects/synthetic-record-full");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find public information" }).click();
  await expect(
    page.locator("[data-slot=public-discovery-results] [data-slot=discovery-source]").first()
  ).toBeVisible();
});

test("nothing is prefetched, and no data-saving signal turns the mode on by itself", async ({
  page
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "connection", {
      configurable: true,
      value: { saveData: true }
    });
  });
  const requests: string[] = [];

  page.on("request", (request) => requests.push(request.url()));
  await page.goto("/en/projects");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("html")).toHaveAttribute("data-low-data", "false");
  await expect(toggle(page)).toContainText(
    "Your browser asks to save data. Turn on low-data mode?"
  );
  expect(await page.locator('link[rel="prefetch"], link[rel="prerender"]').count()).toBe(0);
  expect(requests.filter((url) => url.includes("_rsc=") || url.includes("/_next/data/"))).toEqual(
    []
  );

  await toggle(page).getByRole("button", { name: "Not now" }).click();
  await expect(toggle(page)).not.toContainText("asks to save data");
  await expect(page.locator("html")).toHaveAttribute("data-low-data", "false");
});

test("an explicit off is respected even when the browser asks to save data", async ({
  context,
  page,
  baseURL
}) => {
  await context.addCookies([
    { name: "sg_low_data", value: "0", url: baseURL ?? "http://127.0.0.1:3100" }
  ]);
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "connection", {
      configurable: true,
      value: { saveData: true }
    });
  });
  await page.goto("/en");
  await page.waitForLoadState("networkidle");
  await expect(toggle(page)).toContainText("Low-data mode is off");
  await expect(toggle(page)).not.toContainText("asks to save data");
});

test("low-data mode slows Source Scout polling instead of dropping it", async ({
  context,
  page,
  baseURL
}, info) => {
  const gaps: number[] = [];

  await context.addCookies([
    { name: "sg_low_data", value: "1", url: baseURL ?? "http://127.0.0.1:3100" }
  ]);
  let last = 0;

  page.on("request", (request) => {
    if (request.url().includes("/api/public/discovery/")) {
      const now = Date.now();

      if (last !== 0) gaps.push(now - last);
      last = now;
    }
  });
  await page.goto(`/en/projects/${progressSlug(info)}`);
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find public information" }).click();
  await expect(page.locator("[data-slot=project-discovery]")).toContainText("Search completed", {
    timeout: 25000
  });
  expect(gaps.length).toBeGreaterThanOrEqual(1);
  expect(Math.min(...gaps)).toBeGreaterThanOrEqual(3500);
});
