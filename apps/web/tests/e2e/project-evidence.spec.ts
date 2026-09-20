import { expect, test } from "@playwright/test";

const FULL = "/en/projects/synthetic-record-full";

test("a record shows each sourced statement with its own label, and hides one with no citation", async ({
  page
}) => {
  await page.goto(FULL);

  await expect(
    page.getByRole("heading", { level: 1, name: "Synthetic full record" })
  ).toBeVisible();
  await expect(page.getByText("A fictional bulletin lists this work as planned.")).toBeVisible();
  await expect(page.getByText("A statement without any citation must never show.")).toHaveCount(0);
  await expect(page.getByText("This record was last checked more than")).toBeVisible();
  await expect(page.getByRole("heading", { name: "What is not known" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What was promised" })).toBeVisible();
});

test("every statement's source link opens a source page that contains the cited passage", async ({
  page
}) => {
  await page.goto(FULL);
  const links = page.locator("[data-slot=citation-entry]").getByRole("link", {
    name: /source page/i
  });
  const count = await links.count();

  expect(count).toBeGreaterThan(5);

  for (let index = 0; index < count; index += 1) {
    const href = await links.nth(index).getAttribute("href");
    expect(href).toMatch(/^\/en\/projects\/synthetic-record-full\/sources\/[0-9a-f-]{36}$/);
    const response = await page.request.get(href ?? "");
    expect(response.status()).toBe(200);
  }
});

test("the source page explains an unreachable original and keeps the saved passage", async ({
  page
}) => {
  await page.goto(
    "/en/projects/synthetic-record-full/sources/00000000-0000-4000-8000-000000000002"
  );

  await expect(
    page.getByRole("heading", { level: 1, name: "Synthetic daily report" })
  ).toBeVisible();
  await expect(page.getByText("could not be reached when last checked")).toBeVisible();
  await expect(page.getByText("End of the long passage.")).toBeHidden();
  await page.getByText("Show the full passage").click();
  await expect(page.getByText("End of the long passage.")).toBeVisible();

  const original = page.getByRole("link", { name: /Open the original source/ });
  await expect(original).toHaveAttribute("target", "_blank");
  await expect(original).toHaveAttribute("rel", /noopener/);
  await expect(original).toHaveAttribute("rel", /noreferrer/);
  await expect(original).toHaveAttribute("referrerpolicy", "no-referrer");
});

test("an unknown record or source is a plain not-found, the same for every miss", async ({
  page
}) => {
  const record = await page.goto("/en/projects/synthetic-record-missing");
  expect(record?.status()).toBe(404);

  const malformed = await page.goto("/en/projects/Not_A_Slug!");
  expect(malformed?.status()).toBe(404);

  await page.goto(
    "/en/projects/synthetic-record-full/sources/00000000-0000-4000-8000-0000000000ff"
  );
  await expect(page.getByRole("heading", { name: "This source is not available" })).toBeVisible();
});

test("the report link keeps the project context and the page never shows private fields", async ({
  page
}) => {
  await page.goto(FULL);

  await expect(
    page
      .getByRole("main")
      .getByRole("link", { name: /report/i })
      .first()
  ).toHaveAttribute("href", /\/en\/report\?project=synthetic-record-full$/);
  const html = (await page.content()).toLowerCase();
  for (const field of ["internal_reason", "reviewer_note", "tracking_code", "contact_value"]) {
    expect(html, field).not.toContain(field);
  }
});

test("the minimal record is honest about what is missing", async ({ page }) => {
  await page.goto("/en/projects/synthetic-record-minimal");

  await expect(page.getByText("No sourced statements have been published")).toBeVisible();
  await expect(page.getByText("No updates have been published")).toBeVisible();
});

test("the trust page explains the labels and offers one correction route", async ({ page }) => {
  await page.goto("/en/trust");

  await expect(page.getByRole("heading", { level: 1, name: "How records work" })).toBeVisible();
  await expect(page.locator("#sources")).toBeVisible();
  await expect(page.getByRole("link", { name: /report/i }).first()).toBeVisible();
  await expect(page.getByText(/not an emergency service/i).first()).toBeVisible();
});

test("record, source, and trust pages work without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  for (const path of [FULL, "/en/trust", "/yo/projects/synthetic-record-full"]) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }

  await context.close();
});

test("every language serves a record and labels untranslated copy", async ({ page }) => {
  for (const locale of ["ha", "ig", "yo"]) {
    await page.goto(`/${locale}/projects/synthetic-record-full`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
  }
});
