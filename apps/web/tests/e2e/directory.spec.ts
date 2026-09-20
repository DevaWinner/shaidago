import { expect, test, type Page } from "@playwright/test";

import { readFileSync } from "node:fs";
import { join } from "node:path";

import type EnglishMessages from "../../messages/en.json";

// Playwright cannot import JSON; the Hausa catalogue is read from disk.
const ha = JSON.parse(
  readFileSync(join(import.meta.dirname, "..", "..", "messages", "ha.json"), "utf8")
) as typeof EnglishMessages;

const results = (page: Page) => page.locator("[data-slot=project-card]");

test("the first page shows twelve records with a clear action, a count, and a way forward", async ({
  page
}) => {
  await page.goto("/en/projects");

  await expect(page.getByRole("heading", { level: 1, name: "Project records" })).toBeVisible();
  await expect(results(page)).toHaveCount(12);
  await expect(
    page.getByRole("status").filter({ hasText: "Showing 12 project records." })
  ).toBeVisible();
  const first = results(page).first();
  await expect(first.getByRole("link", { name: "Synthetic example project 01" })).toHaveAttribute(
    "href",
    "/en/projects/synthetic-project-01"
  );
  await expect(first.getByText("Recorded status")).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "Project record pages" })
      .getByRole("link", { name: "Next records" })
  ).toBeVisible();
});

test("pagination follows the opaque cursor to the end and can return to the first page", async ({
  page
}) => {
  await page.goto("/en/projects");
  await page.getByRole("link", { name: "Next records" }).click();

  await expect(page).toHaveURL(/cursor=/);
  await expect(results(page)).toHaveCount(12);
  await expect(results(page).first().getByRole("link")).toHaveText("Synthetic example project 13");
  await page.getByRole("link", { name: "Next records" }).click();
  await expect(results(page)).toHaveCount(6);
  await expect(page.getByRole("link", { name: "Next records" })).toHaveCount(0);
  await page.getByRole("link", { name: "Back to the first page" }).click();
  await expect(page).not.toHaveURL(/cursor=/);
  await expect(results(page)).toHaveCount(12);
});

test("the form filters through the URL, shows removable filters, and clear all is one link", async ({
  page
}) => {
  await page.goto("/en/projects");
  await page.getByLabel("Category").selectOption("health");
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page).toHaveURL(/\/en\/projects\?category=health#results$/);
  await expect(results(page).first()).toContainText("Health");
  const pills = page.getByRole("navigation", { name: "Active filters" });
  await expect(pills.getByRole("link", { name: "Remove filter: Health" })).toBeVisible();

  await page.getByLabel("Locality").selectOption("amac");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/\?locality=amac&category=health#results$/);

  await pills.getByRole("link", { name: "Remove filter: Health" }).click();
  await expect(page).toHaveURL(/\/en\/projects\?locality=amac#results$/);
  await page.getByRole("link", { name: "Clear all filters" }).click();
  await expect(page).toHaveURL(/\/en\/projects#results$/);
  await expect(page.getByRole("navigation", { name: "Active filters" })).toHaveCount(0);
});

test("a shared URL restores the same filters and results", async ({ page }) => {
  await page.goto("/en/projects?q=example&locality=bwari&status=planned");

  await expect(page.getByLabel("Search project records")).toHaveValue("example");
  await expect(page.getByLabel("Locality")).toHaveValue("bwari");
  await expect(page.getByLabel("Recorded status")).toHaveValue("planned");
  for (const card of await results(page).all()) {
    await expect(card).toContainText("Planned");
  }
});

test("unknown values and stray parameters are corrected to a canonical URL, never sent to the backend", async ({
  page
}) => {
  await page.goto("/en/projects?category=weapons&utm_source=x&locality=nowhere&cursor=%25%25");

  await expect(page).toHaveURL(/\/en\/projects(#results)?$/);
  await expect(results(page)).toHaveCount(12);

  await page.goto("/en/projects?q=%20%20example%20%20&category=health");
  await expect(page).toHaveURL(/\/en\/projects\?q=example&category=health(#results)?$/);
});

test("no matches keeps the filters visible and offers one way out", async ({ page }) => {
  await page.goto("/en/projects?q=zzzz-nothing-matches");

  await expect(page.getByRole("heading", { name: "No records match these filters" })).toBeVisible();
  await expect(
    page.getByRole("status").filter({ hasText: "No records match these filters" })
  ).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Active filters" })).toBeVisible();
  await page.getByRole("main").getByRole("link", { name: "Clear all filters" }).last().click();
  await expect(results(page)).toHaveCount(12);
});

test("a cursor that is well formed but no longer valid recovers to the first page", async ({
  page
}) => {
  await page.goto("/en/projects?cursor=stale-cursor-value");

  await expect(
    page.getByRole("heading", { name: "That page of results is no longer valid" })
  ).toBeVisible();
  await page.getByRole("link", { name: "Go to the first page" }).click();
  await expect(results(page)).toHaveCount(12);
});

test("an unavailable service is stated plainly, with retry, and the page stays usable", async ({
  page
}) => {
  await page.goto("/en/projects?q=__unavailable");

  await expect(
    page.getByRole("heading", { name: "Project records could not be loaded" })
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Try again" })).toBeVisible();
  await expect(page.getByLabel("Search project records")).toBeVisible();
  const text = await page.locator("main").innerText();
  expect(text).not.toContain("synthetic detail that must never be shown");
  expect(text).not.toContain("dependency_unavailable");
});

test("freshness is stated in words, and a missing check date is shown as such", async ({
  page
}) => {
  await page.goto("/en/projects");

  await expect(results(page).nth(3)).toContainText("Not yet checked");
  await expect(results(page).nth(5)).toContainText("Last checked more than 90 days ago.");
  await expect(results(page).first().locator("time")).toHaveAttribute(
    "datetime",
    /^\d{4}-\d{2}-\d{2}$/
  );
});

test("with JavaScript, a filter change moves focus to the results", async ({ page }) => {
  await page.goto("/en/projects");
  await page.getByLabel("Category").selectOption("education");
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page.locator("#results")).toBeFocused();
});

test("language links keep the filters, drop the cursor, and the original-language notice is shown", async ({
  page
}) => {
  await page.goto("/en/projects?q=example");
  const cursor = await page.getByRole("link", { name: "Next records" }).getAttribute("href");
  expect(cursor).toContain("cursor=");

  await page.goto(`/en${cursor?.slice("/en".length)}`);
  const hausa = page
    .getByRole("navigation", { name: "Language" })
    .getByRole("link", { name: "Hausa" });
  await expect(hausa).toHaveAttribute("href", "/ha/projects?q=example");

  await hausa.click();
  await expect(page).toHaveURL(/\/ha\/projects\?q=example$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "ha");
  await expect(page.getByText(ha.evidence.translation.unavailable).first()).toBeVisible();
});

test("the directory works with JavaScript disabled, through plain form and link navigation", async ({
  browser
}) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  await page.goto("http://127.0.0.1:3100/en/projects");
  await page.getByLabel("Recorded status").selectOption("planned");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/status=planned/);
  await page.getByRole("link", { name: "Remove filter: Planned" }).click();
  await expect(page).not.toHaveURL(/status=/);
  await page.getByRole("link", { name: "Next records" }).click();
  await expect(page).toHaveURL(/cursor=/);
  await context.close();
});

test("the results have stable landmarks and one h1", async ({ page }) => {
  await page.goto("/en/projects");

  await expect(page.getByRole("banner")).toBeVisible();
  await expect(page.getByRole("main")).toBeVisible();
  await expect(
    page.getByRole("search", { name: "Search and filter project records" })
  ).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
  await expect(page.getByRole("contentinfo")).toBeVisible();
});
