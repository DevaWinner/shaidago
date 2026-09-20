import { gzipSync } from "node:zlib";

import { expect, test, type Page } from "@playwright/test";

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
  "/en/trust"
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
