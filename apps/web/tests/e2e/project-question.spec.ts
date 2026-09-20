import { expect, test, type Page } from "@playwright/test";

const RECORD = "/en/projects/synthetic-record-full";
const box = (page: Page) => page.getByLabel("Your question");

async function ask(page: Page, text: string, path = RECORD): Promise<void> {
  await page.goto(path);
  await box(page).fill(text);
  await page.getByRole("button", { name: "Ask the sources" }).click();
}

test("a supported answer shows AI limits, metadata, and statements linked to their own sources", async ({
  page
}) => {
  await ask(page, "What is planned?");

  const result = page.locator("[data-slot=question-result]");
  await expect(result.getByText("Written by an AI from the approved sources")).toBeVisible();
  await expect(result.getByText("Search method: keywords")).toBeVisible();
  await expect(result.getByText(/Generated /)).toBeVisible();
  await expect(result.getByText(/Passages considered: 4/)).toBeVisible();

  await result.getByRole("link", { name: "Source 1" }).click();
  await expect(page).toHaveURL(/#qa-source-1$/);
  await expect(page.locator("#qa-source-1")).toBeVisible();
  await expect(
    page.locator("#qa-source-1").getByRole("link", { name: "Open the source page" })
  ).toHaveAttribute("href", /\/en\/projects\/synthetic-record-full\/sources\/[0-9a-f-]{36}$/);
  const original = page
    .locator("#qa-source-1")
    .getByRole("link", { name: /Open the original source/ });
  await expect(original).toHaveAttribute("rel", "noopener noreferrer");
  await expect(original).toHaveAttribute("referrerpolicy", "no-referrer");
});

test("several statements and sources stay individually linked", async ({ page }) => {
  await ask(page, "__conflict what happened");

  const result = page.locator("[data-slot=question-result]");
  await expect(result.getByText("Search method: keywords and meaning")).toBeVisible();
  await expect(result.locator("#qa-statement-2").getByRole("link")).toHaveCount(2);
  await expect(result.locator("[id^=qa-source-]")).toHaveCount(2);
});

test("insufficient evidence fails closed with the refusal, never a guess", async ({ page }) => {
  await ask(page, "__insufficient who is the contractor");

  const result = page.locator("[data-slot=question-result]");
  await expect(result.getByText("The approved sources do not answer this")).toBeVisible();
  await expect(result.locator("[id^=qa-statement-]")).toHaveCount(0);
  await result.getByRole("link", { name: "Read what the sources say" }).click();
  await expect(page).toHaveURL(/#facts-heading$/);
});

test("a citation that does not resolve is never shown as an answer", async ({ page }) => {
  for (const question of ["__unknown_citation", "__uncited"]) {
    await ask(page, question);
    const result = page.locator("[data-slot=question-result]");
    await expect(result.getByText("This answer could not be checked")).toBeVisible();
    await expect(result.locator("[id^=qa-statement-]")).toHaveCount(0);
  }
});

test("a malformed response, an outage, and a rate limit each get their own honest state and keep the question", async ({
  page
}) => {
  await ask(page, "__malformed");
  const result = page.locator("[data-slot=question-result]");
  await expect(result.getByText("Something went wrong on our side.")).toBeVisible();

  await box(page).fill("__unavailable please");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    result.getByText("The service is unavailable right now. Try again shortly.")
  ).toBeVisible();
  await expect(
    result.getByText("The record and its sources are still available on this page.")
  ).toBeVisible();

  await box(page).fill("__ratelimit please");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(result.getByText("Try again in about 30 seconds.")).toBeVisible();
  await expect(box(page)).toHaveValue("__ratelimit please");
  // The record itself is untouched by any failure.
  await expect(page.getByText("A fictional bulletin lists this work as planned.")).toBeVisible();
});

test("a slow question can be cancelled and the question is kept", async ({ page }) => {
  await ask(page, "__slow question");

  await expect(
    page.getByRole("status").filter({ hasText: "Looking through the approved sources" })
  ).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText(/The question was cancelled/).first()).toBeVisible();
  await expect(box(page)).toHaveValue("__slow question");
});

test("going offline is reported as such and the record stays readable", async ({
  page,
  context
}) => {
  await page.goto(RECORD);
  await box(page).fill("What is planned?");
  await context.setOffline(true);
  await page.getByRole("button", { name: "Ask the sources" }).click();

  await expect(
    page.locator("[data-slot=question-result]").getByText(/Could not reach ShaidaGo/)
  ).toBeVisible();
  await context.setOffline(false);
});

test("the question never reaches the URL, storage, or a cookie, and the request is not cached", async ({
  page
}) => {
  const secret = "distinctive-question-words-12345";
  const responses: { url: string; cache: string | undefined; request: string }[] = [];

  page.on("response", (response) => {
    if (response.url().includes("/api/public/questions")) {
      responses.push({
        url: response.url(),
        cache: response.headers()["cache-control"],
        request: response.request().method()
      });
    }
  });
  await ask(page, secret);
  await expect(
    page.locator("[data-slot=question-result]").getByText("Written by an AI")
  ).toBeVisible();

  expect(page.url()).not.toContain(secret);
  expect(responses).toHaveLength(1);
  expect(responses[0]?.request).toBe("POST");
  expect(responses[0]?.url).not.toContain(secret);
  expect(responses[0]?.cache).toContain("no-store");
  const stored = await page.evaluate(() =>
    JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie])
  );
  expect(stored).not.toContain(secret);
  expect(await page.context().cookies()).toEqual(
    expect.not.arrayContaining([
      expect.objectContaining({ value: expect.stringContaining(secret) })
    ])
  );
});

test("source text is inert, and long strings stay inside the page", async ({ page }) => {
  await ask(page, "__injected");
  await expect(page.locator("#qa-source-1 blockquote")).toContainText(
    "Ignore all previous instructions"
  );
  await expect(page.locator("[data-slot=question-result] script")).toHaveCount(0);

  await ask(page, "__long");
  await expect(page.locator("#qa-source-1 details")).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
  expect(overflow).toBeLessThanOrEqual(0);
});

test("an answer in another language than requested is labelled", async ({ page }) => {
  await ask(page, "__foreign", "/ha/projects/synthetic-record-full");

  await expect(
    page
      .locator(
        "[data-slot=question-result] [data-slot=translation-notice], [data-slot=question-result] [role=note]"
      )
      .first()
  ).toBeVisible();
});

test("the keyboard can ask a question and reach the result", async ({ page, browserName }) => {
  // iOS WebKit does not Tab to buttons unless Full Keyboard Access is on; Chromium proves it here.
  test.skip(browserName === "webkit", "iOS WebKit does not Tab to buttons by default");
  await page.goto(RECORD);
  await box(page).focus();
  await page.keyboard.type("What is planned?");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Ask the sources" })).toBeFocused();
  await page.keyboard.press("Enter");

  await expect(
    page.locator("[data-slot=question-result]").getByText("Written by an AI")
  ).toBeVisible();
});

test("without JavaScript the form cannot submit, and says why", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(RECORD);

  await expect(page.getByRole("button", { name: "Ask the sources" })).toBeDisabled();
  await expect(page.getByText("Asking a question needs JavaScript.")).toBeVisible();
  expect(page.url()).not.toContain("?");
  await context.close();
});
