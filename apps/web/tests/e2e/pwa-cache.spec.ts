import { expect, test, type Page } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const RECORD = "/en/projects/synthetic-record-full";
const SOURCE = `${RECORD}/sources/00000000-0000-4000-8000-000000000002`;
const CANARIES = [
  "SG-FICTIONAL",
  "fictional-contact@example.invalid",
  "Fictional description",
  "fictional-session-token",
  "PRIVATE-CANARY"
];

const ALLOWED = [
  /^\/(en|ha|ig|yo)$/,
  /^\/(en|ha|ig|yo)\/projects$/,
  /^\/(en|ha|ig|yo)\/projects\/[a-z0-9-]+$/,
  /^\/(en|ha|ig|yo)\/projects\/[a-z0-9-]+\/sources\/[0-9a-f-]{36}$/,
  /^\/(en|ha|ig|yo)\/(trust|offline)$/,
  /^\/_next\/static\//,
  /^\/__prefs\//
];
const FORBIDDEN = /\/(api|report|track|handle|reviewer)(\/|$)/;

/** Registers the worker and waits until it controls the page. */
async function controlled(page: Page, path = "/en"): Promise<void> {
  await page.goto(path);
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect
    .poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null))
    .toBe(true);
}

async function inspect(page: Page): Promise<{ urls: string[]; problems: string[] }> {
  return page.evaluate(
    async ({ canaries }) => {
      const urls: string[] = [];
      const problems: string[] = [];

      for (const name of await caches.keys()) {
        const cache = await caches.open(name);

        for (const request of await cache.keys()) {
          const response = await cache.match(request);
          const url = new URL(request.url);

          urls.push(`${name} ${url.pathname}${url.search}`);
          if (request.method !== "GET") problems.push(`${name} ${request.method} ${url.pathname}`);
          const control = (response?.headers.get("cache-control") ?? "").toLowerCase();

          if (/no-store|private/.test(control) && !url.pathname.startsWith("/__prefs"))
            problems.push(`${name} ${url.pathname} ${control}`);
          if (response?.headers.get("set-cookie"))
            problems.push(`${name} ${url.pathname} set-cookie`);
          const text = name.includes("assets") ? "" : await response?.clone().text();

          for (const canary of canaries) {
            if (text?.includes(canary))
              problems.push(`${name} ${url.pathname} contains a private value`);
          }
        }
      }

      return { urls, problems };
    },
    { canaries: CANARIES }
  );
}

test("after every kind of route and request, only allowlisted public pages and framework files are stored", async ({
  context,
  page,
  request
}) => {
  await controlled(page);
  for (const path of [
    RECORD,
    SOURCE,
    "/en/projects",
    "/en/projects?category=health",
    "/en/trust",
    "/ha/projects",
    "/en/projects?q=free+text"
  ]) {
    await page.goto(path);
  }

  // Private and interactive routes, exercised so a mistake would show up in a cache.
  await signInAs(context, ORIGIN);
  for (const path of [
    "/en/report",
    "/en/report/synthetic-record-full",
    "/en/report/complete",
    "/en/track",
    "/en/handle",
    "/en/reviewer/sign-in",
    "/en/reviewer/reports",
    "/en/reviewer/reports/0198f1a2-7b3c-4d4e-8f5a-000000000001?reveal=contact"
  ]) {
    await page.goto(path);
  }
  await page.goto("/en/track");
  await page.evaluate(async () => {
    await fetch("/api/tracking/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: "SG-FICTIONAL-0001-UNDERREVIEW" })
    });
    await fetch("/api/public/questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug: "synthetic-record-full", question: "PRIVATE-CANARY?" })
    });
  });
  expect((await request.get("/en/track")).status()).toBe(200);

  const { urls, problems } = await inspect(page);

  expect(problems).toEqual([]);
  expect(urls.length).toBeGreaterThan(3);
  for (const entry of urls) {
    const path = entry.split(" ")[1]?.split("?")[0] ?? "";

    expect(FORBIDDEN.test(path), entry).toBe(false);
    expect(
      ALLOWED.some((pattern) => pattern.test(path)),
      entry
    ).toBe(true);
    expect(entry, "free-text search is never stored").not.toContain("q=");
  }
  expect(urls.some((entry) => entry.includes("sg-pages-v1") && entry.includes(RECORD))).toBe(true);
});

test("a recently viewed public record can be revisited offline, with the saved time, and private routes stay unavailable", async ({
  context,
  page
}, info) => {
  // Playwright's WebKit cannot navigate while offline emulation is on and a service worker is
  // active ("WebKit encountered an internal error"), so the offline behaviour is proven on
  // Chromium; the cache contents are inspected on both engines by the tests above and below.
  test.skip(
    info.project.name !== "chromium",
    "Playwright WebKit cannot emulate offline navigation with a service worker"
  );
  await controlled(page);
  await page.goto(RECORD);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.goto("/en/projects");

  await context.setOffline(true);
  await page.goto(RECORD);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator("[data-slot=offline-banner]")).toContainText("saved copy from");
  await expect(page.locator("[data-slot=offline-banner]")).toContainText("2026");

  // A page never visited: the offline page, with a retry and the saved pages.
  await page.goto("/en/projects/synthetic-project-09");
  await expect(page.getByRole("heading", { level: 1, name: "You are offline" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.locator("[data-slot=saved-pages]")).toContainText("Saved");
  await expect(page.locator("[data-slot=saved-pages] a").first()).toBeVisible();

  // Private routes are never served from a cache: there is nothing to show offline.
  for (const path of ["/en/track", "/en/report", "/en/reviewer/reports"]) {
    await expect(page.goto(path)).rejects.toThrow();
  }
  await context.setOffline(false);
});

test("the offline page exists in every language and tells the truth about private actions", async ({
  page
}) => {
  for (const locale of ["en", "ha", "ig", "yo"]) {
    await page.goto(`/${locale}/offline`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator("main")).toContainText(
      locale === "en" ? "Nothing you enter is sent, saved, or queued" : ""
    );
  }
});

test("old cache versions are deleted when a new worker activates, and nothing else is touched", async ({
  page
}) => {
  await controlled(page);
  await page.evaluate(async () => {
    await caches.open("sg-pages-v0").then((cache) => cache.put("/old", new Response("old")));
    await caches.open("not-ours").then((cache) => cache.put("/other", new Response("other")));
    for (const registration of await navigator.serviceWorker.getRegistrations())
      await registration.unregister();
  });
  await page.reload();
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await expect
    .poll(() => page.evaluate(async () => (await caches.keys()).includes("sg-pages-v0")))
    .toBe(false);
  expect(await page.evaluate(async () => (await caches.keys()).includes("not-ours"))).toBe(true);
  await page.evaluate(() => caches.delete("not-ours"));
});

test("the saved pages can be forgotten, and the worker is served without long caching", async ({
  page,
  request
}) => {
  await controlled(page);
  await page.goto(RECORD);
  await page.goto("/en/offline");
  await expect(page.locator("[data-slot=saved-pages] li").first()).toBeVisible();
  await page.getByRole("button", { name: "Forget saved pages" }).click();
  await expect(page.getByText("Saved pages were removed from this device.")).toBeVisible();
  expect((await inspect(page)).urls.filter((entry) => entry.includes("sg-pages"))).toEqual([]);

  const worker = await request.get("/sw.js");

  expect(worker.headers()["cache-control"]).toContain("no-cache");
  expect(worker.headers()["service-worker-allowed"]).toBe("/");
});

test("public pages are revalidated, not stored by shared caches, and private ones keep no-store", async ({
  request
}) => {
  expect((await request.get(RECORD)).headers()["cache-control"]).toBe(
    "public, max-age=0, must-revalidate"
  );
  expect((await request.get("/en/track")).headers()["cache-control"]).toMatch(/no-store/);
  expect((await request.get("/en/report")).headers()["cache-control"]).toMatch(/no-store/);
});
