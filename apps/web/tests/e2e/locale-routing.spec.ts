import { expect, test } from "@playwright/test";

import { readFileSync } from "node:fs";
import { join } from "node:path";

import type EnglishMessages from "../../messages/en.json";

// Playwright's ESM loader cannot import JSON, so the catalogues are read from disk. The English
// type gives every locale's catalogue the same checked shape (see `pnpm run messages:check`).
const catalogue = (name: string): typeof EnglishMessages =>
  JSON.parse(
    readFileSync(join(import.meta.dirname, "..", "..", "messages", `${name}.json`), "utf8")
  ) as typeof EnglishMessages;
const en = catalogue("en");
const ha = catalogue("ha");
const ig = catalogue("ig");
const yo = catalogue("yo");

test("a bare visit lands on the English route and keeps the query", async ({ page }) => {
  await page.goto("/?locality=amac&q=clinic");

  expect(new URL(page.url()).pathname).toBe("/en");
  expect(new URL(page.url()).search).toBe("?locality=amac&q=clinic");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("Accept-Language chooses a supported locale and an unsupported one falls back to English", async ({
  browser
}) => {
  const hausa = await browser.newContext({
    locale: "ha-NG",
    extraHTTPHeaders: { "Accept-Language": "ha" }
  });
  const hausaPage = await hausa.newPage();
  await hausaPage.goto("/");
  expect(new URL(hausaPage.url()).pathname).toBe("/ha");
  await hausa.close();

  const french = await browser.newContext({
    extraHTTPHeaders: { "Accept-Language": "fr-FR,de;q=0.8" }
  });
  const frenchPage = await french.newPage();
  await frenchPage.goto("/");
  expect(new URL(frenchPage.url()).pathname).toBe("/en");
  await french.close();
});

for (const locale of ["ha", "ig", "yo"] as const) {
  test(`${locale} serves its own reviewed copy in its own language`, async ({ page }) => {
    const copy = { ha, ig, yo }[locale];
    const response = await page.goto(`/${locale}`);

    expect(response?.status()).toBe(200);
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(copy.landing.heading);
    await expect(page.getByRole("link", { name: copy.landing.browse })).toBeVisible();
    await expect(page.getByRole("link", { name: copy.landing.report })).toBeVisible();
    await expect(page.getByText(copy.shell.public.notEmergency)).toBeVisible();
    // Nothing falls back to English: no notice, and no language is labelled unreviewed.
    await expect(page.getByText(en.evidence.translation.unavailable)).toHaveCount(0);
    await expect(page.getByText(`(${en.shell.public.localeUnavailable})`)).toHaveCount(0);
    const control = page.getByRole("navigation", { name: copy.shell.public.localeLabel });
    await expect(control.getByText(copy.shell.public.localeNames[locale])).toHaveAttribute(
      "aria-current",
      "true"
    );
  });
}

test("English stays the source language and needs no notice", async ({ page }) => {
  await page.goto("/en");

  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(en.landing.heading);
  await expect(page.getByText(en.evidence.translation.unavailable)).toHaveCount(0);
});
test("the language cookie is remembered, holds only a locale code, and wins over the header", async ({
  browser
}) => {
  const context = await browser.newContext({ extraHTTPHeaders: { "Accept-Language": "ig" } });
  const page = await context.newPage();

  await page.goto("/yo");
  const cookies = await context.cookies();
  const preference = cookies.find((cookie) => cookie.name === "NEXT_LOCALE");
  expect(preference?.value).toBe("yo");
  expect(preference?.httpOnly).toBe(false);
  expect(preference?.sameSite).toBe("Lax");
  expect(cookies.map((cookie) => cookie.name)).toEqual(["NEXT_LOCALE"]);

  await page.goto("/");
  expect(new URL(page.url()).pathname).toBe("/yo");
  await context.close();
});

test("an unsupported first segment becomes a path under English and is a shell-wrapped 404", async ({
  page
}) => {
  const response = await page.goto("/xx/foo");

  expect(new URL(page.url()).pathname).toBe("/en/xx/foo");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "This page is not available" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("link", { name: "Return to ShaidaGo" })).toHaveAttribute("href", "/");
});

test("an unknown path under a real locale is a 404 in that locale", async ({ page }) => {
  const response = await page.goto("/ig/not-a-real-record");

  expect(response?.status()).toBe(404);
  await expect(page.getByRole("link", { name: "Return to ShaidaGo" })).toHaveAttribute("href", "/");

  // The remembered language brings the visitor back to the same locale.
  await page.getByRole("link", { name: "Return to ShaidaGo" }).click();
  await expect(page).toHaveURL(/\/ig$/);
});

test("open-redirect attempts never leave this origin", async ({ request, baseURL }) => {
  for (const path of ["//evil.example", "/%2F%2Fevil.example", "/\\evil.example"]) {
    // Concatenate: a leading `//` would otherwise be read as a protocol-relative URL to another host.
    const response = await request.get(`${baseURL}${path}`, { maxRedirects: 0 });
    const target = response.headers()["location"];

    if (target !== undefined) {
      expect(new URL(target, baseURL).origin, path).toBe(new URL(baseURL ?? "").origin);
    }
  }
});

test("the BFF and files stay unprefixed and are not redirected", async ({ request }) => {
  const bff = await request.post("/api/tracking/lookup", {
    data: { code: "x" },
    maxRedirects: 0
  });
  expect(bff.status()).not.toBe(307);
  expect(bff.status()).not.toBe(308);
  expect(bff.headers()["location"]).toBeUndefined();
  expect(bff.headers()["content-type"]).toContain("application/problem+json");

  const robots = await request.get("/robots.txt", { maxRedirects: 0 });
  expect(robots.status()).toBe(200);
});

test("language links work without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  await page.goto("http://127.0.0.1:3100/en");
  await page
    .getByRole("navigation", { name: "Language" })
    .getByRole("link", { name: "Igbo" })
    .click();
  expect(new URL(page.url()).pathname).toBe("/ig");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await context.close();
});
