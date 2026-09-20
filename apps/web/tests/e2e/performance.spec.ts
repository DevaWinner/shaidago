import { gzipSync } from "node:zlib";

import { expect, test, type Page } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const BUDGET_BYTES = 170 * 1024; // IMPLEMENTATION_PLAN: public first route, compressed first-load JavaScript

/** Total gzip size of every script the page loads before it is idle. */
async function firstLoadScriptBytes(
  page: Page,
  path: string
): Promise<{ bytes: number; files: number }> {
  const scripts: Promise<number>[] = [];

  page.on("response", (response) => {
    if (response.request().resourceType() === "script") {
      scripts.push(response.body().then((body) => gzipSync(body, { level: 9 }).length));
    }
  });
  await page.goto(path, { waitUntil: "networkidle" });
  const sizes = await Promise.all(scripts);

  return { bytes: sizes.reduce((sum, size) => sum + size, 0), files: sizes.length };
}

for (const path of [
  "/en",
  "/en/projects",
  "/en/projects?category=health",
  "/ha",
  "/yo/projects",
  "/en/projects/synthetic-record-full",
  "/en/trust",
  "/en/report/synthetic-record-full",
  "/en/report/complete",
  "/en/track",
  "/en/handle"
]) {
  test(`first-load JavaScript for ${path} stays inside the plan's budget`, async ({
    page
  }, info) => {
    const { bytes, files } = await firstLoadScriptBytes(page, path);

    info.annotations.push({
      type: "first-load JS (gzip)",
      description: `${(bytes / 1024).toFixed(1)} KB in ${files} files`
    });
    expect(bytes).toBeLessThan(BUDGET_BYTES);
  });
}

test("the directory adds no client framework of its own: filtering is a plain form and links", async ({
  page
}) => {
  await page.goto("/en/projects");

  // The only interactive behaviour is server-rendered HTML; the form has no client submit handler.
  expect(await page.locator("form[role=search]").getAttribute("method")).toBe("get");
  expect(await page.locator("form[role=search]").getAttribute("action")).toBe(
    "/en/projects#results"
  );
  expect(await page.locator("script[type='text/javascript']").count()).toBe(0);
});

// Route-scoped budgets for the authenticated tools, measured on the built app (gzip, first load).
// They are looser than the public budget because a reviewer needs forms, dialogs, and previews on
// one page; each figure is the measured size plus headroom, so a regression shows. Measured
// 2026-09-20: sign-in 171.3 KB, queue 169.0 KB, report detail 198.7 KB (225.5 KB before the message
// formatter stopped importing every language's catalogue).
const REVIEWER_BUDGETS: readonly (readonly [string, number])[] = [
  ["/en/reviewer/sign-in", 180],
  ["/en/reviewer/reports", 180],
  ["/en/reviewer/reports/0198f1a2-7b3c-4d4e-8f5a-000000000001", 210]
];

for (const [path, kilobytes] of REVIEWER_BUDGETS) {
  test(`first-load JavaScript for ${path} stays inside its route budget of ${kilobytes} KB`, async ({
    context,
    page
  }, info) => {
    await signInAs(context, "http://127.0.0.1:3100");
    const { bytes, files } = await firstLoadScriptBytes(page, path);

    info.annotations.push({
      type: "first-load JS (gzip)",
      description: `${(bytes / 1024).toFixed(1)} KB in ${files} files`
    });
    expect(bytes).toBeLessThan(kilobytes * 1024);
  });
}

test("loading a page makes no API request of its own, so there is nothing to multiply", async ({
  context,
  page
}) => {
  const calls: string[] = [];

  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/")) calls.push(request.url());
  });
  await signInAs(context, "http://127.0.0.1:3100");
  for (const path of [
    "/en/projects/synthetic-record-full",
    "/en/reviewer/reports",
    "/en/reviewer/reports/0198f1a2-7b3c-4d4e-8f5a-000000000001"
  ]) {
    await page.goto(path, { waitUntil: "networkidle" });
  }
  expect(calls).toEqual([]);
});

test("long lists are paged, so the page never holds more than one bounded page of results", async ({
  context,
  page
}) => {
  await page.goto("/en/projects", { waitUntil: "networkidle" });
  expect(await page.locator("[data-slot=project-card], article").count()).toBeLessThanOrEqual(12);
  await signInAs(context, "http://127.0.0.1:3100");
  await page.goto("/en/reviewer/reports", { waitUntil: "networkidle" });
  expect(await page.locator("[data-slot=queue-item]").count()).toBeLessThanOrEqual(20);
});

test("a slow phone on a slow network still paints, stays stable, and settles (Chromium, 4x CPU, 1.6 Mbps)", async ({
  browser
}, info) => {
  test.skip(
    info.project.name !== "chromium",
    "CPU and network throttling use the Chromium protocol"
  );
  test.setTimeout(60000);
  const results: string[] = [];

  for (const path of [
    "/en",
    "/en/projects/synthetic-record-full",
    "/en/report/synthetic-record-full"
  ]) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const client = await context.newCDPSession(page);

    await client.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    await client.send("Network.enable");
    await client.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 150,
      downloadThroughput: (1.6 * 1024 * 1024) / 8,
      uploadThroughput: (750 * 1024) / 8
    });
    await page.addInitScript(() => {
      const state = { cls: 0, lcp: 0 };

      (window as unknown as { __vitals: typeof state }).__vitals = state;
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as (PerformanceEntry & {
          hadRecentInput?: boolean;
          value?: number;
        })[]) {
          if (!entry.hadRecentInput) state.cls += entry.value ?? 0;
        }
      }).observe({ type: "layout-shift", buffered: true });
      new PerformanceObserver((list) => {
        const last = list.getEntries().at(-1);

        if (last) state.lcp = last.startTime;
      }).observe({ type: "largest-contentful-paint", buffered: true });
    });
    await page.goto(path, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);
    const vitals = await page.evaluate(
      () => (window as unknown as { __vitals: { cls: number; lcp: number } }).__vitals
    );

    results.push(`${path}: LCP ${(vitals.lcp / 1000).toFixed(2)} s, CLS ${vitals.cls.toFixed(3)}`);
    expect(vitals.cls, path).toBeLessThan(0.1);
    expect(vitals.lcp, path).toBeGreaterThan(0);
    expect(vitals.lcp, path).toBeLessThan(4000);
    await context.close();
  }
  info.annotations.push({
    type: "vitals (4x CPU, 1.6 Mbps, 150 ms RTT, localhost server)",
    description: results.join(" | ")
  });
});
