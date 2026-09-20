import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3101";
const LOCALES = ["en", "ha", "ig", "yo"] as const;
const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000001";

const publicRoutes = (locale: string) => [
  `/${locale}`,
  `/${locale}/projects`,
  `/${locale}/projects/synthetic-record-full`,
  `/${locale}/projects/synthetic-record-full/sources/00000000-0000-4000-8000-000000000002`,
  `/${locale}/trust`,
  `/${locale}/report/synthetic-record-full`,
  `/${locale}/track`,
  `/${locale}/handle`,
  `/${locale}/offline`
];
const reviewerRoutes = (locale: string) => [
  `/${locale}/reviewer/sign-in`,
  `/${locale}/reviewer/reports`,
  `/${locale}/reviewer/reports/${REPORT}`
];

/** Landmarks, one title, one h1, no skipped heading level, a first-focus skip link, a valid lang. */
async function structure(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  const facts = await page.evaluate(() => {
    const headings = [...document.querySelectorAll("h1, h2, h3, h4, h5, h6")].map((node) =>
      Number(node.tagName.slice(1))
    );
    let skipped = false;

    headings.forEach((level, index) => {
      if (index > 0 && level > (headings[index - 1] ?? 0) + 1) skipped = true;
    });

    return {
      title: document.title.trim(),
      titles: document.querySelectorAll("title").length,
      h1: document.querySelectorAll("h1").length,
      main: document.querySelectorAll("main").length,
      banner: document.querySelectorAll("header, [role=banner]").length,
      lang: document.documentElement.lang,
      skipped,
      firstFocusable:
        (
          document.querySelector(
            "a[href], button, input, select, textarea"
          ) as HTMLAnchorElement | null
        )?.getAttribute("href") ?? ""
    };
  });

  expect(facts.title, path).not.toBe("");
  expect(facts.titles, path).toBe(1);
  expect(facts.h1, path).toBe(1);
  expect(facts.main, path).toBe(1);
  expect(facts.banner, path).toBeGreaterThanOrEqual(1);
  expect(facts.lang, path).toMatch(/^(en|ha|ig|yo)$/);
  expect(facts.skipped, `${path} skips a heading level`).toBe(false);
  expect(facts.firstFocusable, path).toBe("#main-content");
}

for (const locale of LOCALES) {
  test(`${locale}: every public and reviewer route has one title, one h1, one main, no skipped heading, and a skip link`, async ({
    context,
    page
  }) => {
    await signInAs(context, ORIGIN);
    for (const path of [...publicRoutes(locale), ...reviewerRoutes(locale)]) {
      await structure(page, path);
    }
  });
}

test("forced colours keep every control's edge and the page passes axe", async ({
  context,
  page
}) => {
  await page.emulateMedia({ forcedColors: "active" });
  await signInAs(context, ORIGIN);
  for (const path of [
    "/en",
    "/en/projects/synthetic-record-full",
    "/en/report/synthetic-record-full",
    "/en/track",
    `/en/reviewer/reports/${REPORT}`
  ]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    expect((await new AxeBuilder({ page }).analyze()).violations, path).toEqual([]);
    const edges = await page.evaluate(() =>
      [
        ...document.querySelectorAll<HTMLElement>(
          "button, [data-slot=button], input, select, textarea"
        )
      ]
        .filter((node) => node.offsetParent !== null)
        .map((node) => parseFloat(getComputedStyle(node).borderTopWidth))
        .filter((width) => !(width > 0))
    );

    expect(edges, `${path} has a control with no border in forced colours`).toEqual([]);
  }
});

test("reduced motion removes every transition and animation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const path of ["/en", "/en/projects", "/en/report/synthetic-record-full"]) {
    await page.goto(path);
    const moving = await page.evaluate(() =>
      [...document.querySelectorAll<HTMLElement>("*")]
        .filter((node) => {
          const style = getComputedStyle(node);

          return (
            parseFloat(style.transitionDuration) > 0.01 ||
            (style.animationName !== "none" && parseFloat(style.animationDuration) > 0.01)
          );
        })
        .map((node) => node.tagName)
    );

    expect(moving, path).toEqual([]);
  }
});

test("touch targets are at least 44 px and nothing important is hover-only", async ({
  context,
  page
}) => {
  await signInAs(context, ORIGIN);
  for (const path of [
    "/en",
    "/en/projects",
    "/en/report/synthetic-record-full",
    "/en/track",
    `/en/reviewer/reports/${REPORT}`
  ]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const small = await page.evaluate(() =>
      [
        ...document.querySelectorAll<HTMLElement>(
          "button, [data-slot=button], input:not([type=checkbox]):not([type=radio]):not([type=hidden]), select, textarea"
        )
      ]
        .filter((node) => node.offsetParent !== null && !node.closest(".sr-only"))
        .map((node) => ({
          name: node.textContent?.trim().slice(0, 30) || node.tagName,
          height: Math.round(node.getBoundingClientRect().height)
        }))
        .filter((item) => item.height < 44)
    );

    expect(small, path).toEqual([]);
  }
  const css = await page.evaluate(() =>
    [...document.styleSheets]
      .flatMap((sheet) => [...sheet.cssRules].map((rule) => rule.cssText))
      .join("\n")
  );

  expect(css, "no rule reveals content on hover alone").not.toMatch(
    /:hover[^{]*\{[^}]*(display:\s*block|visibility:\s*visible|opacity:\s*1)/
  );
});

const WIDTHS: readonly (readonly [string, number, number])[] = [
  ["low-end phone", 320, 568],
  ["small phone", 360, 640],
  ["modern phone", 390, 844],
  ["phone landscape", 844, 390],
  ["tablet", 768, 1024],
  ["narrow desktop", 1024, 768],
  ["desktop", 1440, 900]
];

test("no page scrolls sideways at any device size, in any language, with dense reviewer data", async ({
  context,
  page
}) => {
  test.setTimeout(90000);
  await signInAs(context, ORIGIN);
  for (const [name, width, height] of WIDTHS) {
    await page.setViewportSize({ width, height });
    for (const path of [
      "/en",
      "/ha/projects",
      "/ig/projects/synthetic-record-full",
      "/yo/report/synthetic-record-full",
      "/en/track",
      "/en/reviewer/reports",
      `/ha/reviewer/reports/${REPORT}`
    ]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      );

      expect(overflow, `${name} ${width}px ${path}`).toBeLessThanOrEqual(0);
    }
  }
});

test("long, unbroken, and maximum-length content wraps in every language instead of scrolling or being cut", async ({
  context,
  page
}) => {
  const long = "Ndi-".repeat(120);
  const overflow = () =>
    page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );

  await signInAs(context, ORIGIN);
  for (const locale of LOCALES) {
    await page.setViewportSize({ width: 320, height: 700 });
    await page.goto(`/${locale}/projects?q=${encodeURIComponent(long.slice(0, 100))}`);
    expect(await overflow(), `${locale} search`).toBeLessThanOrEqual(0);
    await page.goto(`/${locale}/track`);
    await page.waitForLoadState("networkidle");
    await page.getByRole("textbox").first().fill(long);
    expect(await overflow(), `${locale} track`).toBeLessThanOrEqual(0);
    await page.goto(`/${locale}/reviewer/reports/${REPORT}`);
    await page.waitForLoadState("networkidle");
    await page.locator("[data-slot=note-form] textarea").fill(long.repeat(8));
    await page.locator("[data-slot=status-actions] textarea").first().fill(long.repeat(3));
    expect(await overflow(), `${locale} reviewer forms`).toBeLessThanOrEqual(0);
  }
});
