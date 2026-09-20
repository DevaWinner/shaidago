import { expect, test, type Page } from "@playwright/test";

const TRACK = "/en/track";
const SECRET_CODE = "SG-FICTIONAL-0001-UNDERREVIEW";

/** Every request URL and header set this page makes, so a credential can be searched for. */
function watch(page: Page): { urls: string[] } {
  const seen = { urls: [] as string[] };

  page.on("request", (request) => seen.urls.push(request.url()));

  return seen;
}

async function ready(page: Page, path = TRACK): Promise<void> {
  await page.goto(path);
  await expect(page.getByRole("button", { name: "Check status" })).toBeEnabled();
}

const codeBox = (page: Page) => page.getByLabel("Tracking code", { exact: true });
const check = (page: Page) => page.getByRole("button", { name: "Check status" });

async function storageAndCookies(page: Page): Promise<string> {
  const stored = await page.evaluate(() =>
    JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie])
  );

  return stored + JSON.stringify(await page.context().cookies());
}

test("a code is checked by POST only, the box is cleared, and only a public-safe status is shown", async ({
  page
}) => {
  const seen = watch(page);
  const responses: Record<string, string | undefined> = {};

  page.on("response", (response) => {
    if (response.url().includes("/api/tracking/lookup")) {
      responses[response.request().method()] = response.headers()["cache-control"];
    }
  });
  await ready(page);
  await codeBox(page).fill(` ${SECRET_CODE.replaceAll("-", " – ")} `);
  await check(page).click();

  await expect(page.getByText("Status: Under review")).toBeVisible();
  await expect(page.getByText("A reviewer is looking at your report and any files.")).toBeVisible();
  await expect(page.getByText(/Last updated /)).toBeVisible();
  await expect(codeBox(page)).toHaveValue("");
  expect(responses["POST"]).toContain("no-store");
  expect(seen.urls.some((url) => url.includes("FICTIONAL") || url.includes("0001"))).toBe(false);
  expect(page.url()).not.toContain("FICTIONAL");
  expect(await storageAndCookies(page)).not.toContain("FICTIONAL");
  expect(await page.content()).not.toContain("FICTIONAL");
});

test("reloading or going back leaves no status and no code", async ({ page }) => {
  await ready(page);
  await codeBox(page).fill(SECRET_CODE);
  await check(page).click();
  await expect(page.getByText("Status: Under review")).toBeVisible();

  await page.reload();
  await expect(check(page)).toBeEnabled();
  await expect(page.getByText("Status: Under review")).toHaveCount(0);
  expect(await page.content()).not.toContain("FICTIONAL");
  await page.goto("/en");
  await page.goBack();
  await expect(page.getByText("Status: Under review")).toHaveCount(0);
});

test("an unknown code, a rate limit, and an outage each keep the box and say what to do", async ({
  page
}) => {
  await ready(page);
  await codeBox(page).fill("SG-NOTFOUND-1");
  await check(page).click();
  await expect(
    page
      .locator("[data-slot=track-result]")
      .getByText("We could not find a report for that code. Check the code and try again.")
  ).toBeVisible();
  await expect(codeBox(page)).toHaveValue("SG-NOTFOUND-1");

  await codeBox(page).fill("SG-RATELIMIT-1");
  await check(page).click();
  await expect(
    page.locator("[data-slot=track-result]").getByText("Try again in about 30 seconds.")
  ).toBeVisible();

  await codeBox(page).fill("SG-DOWN-1");
  await check(page).click();
  await expect(
    page
      .locator("[data-slot=track-result]")
      .getByText("The service is unavailable right now. Try again shortly.")
  ).toBeVisible();

  await codeBox(page).fill("SG-MALFORMED-1");
  await check(page).click();
  await expect(
    page.locator("[data-slot=track-result]").getByText("Something went wrong on our side.")
  ).toBeVisible();
});

test("every status is explained in words, and the next action is plain", async ({ page }) => {
  await ready(page);
  for (const [code, label, next] of [
    ["SG-CLOSED-1", "Status: Closed", "Nothing more is needed from you right now."],
    ["SG-REFERRED-1", "Status: Referred", "Read where else a concern can be taken."],
    [
      "SG-PUBLIC-1",
      "Status: Checked for a possible public update",
      "Watch the project's public updates."
    ]
  ] as const) {
    await codeBox(page).fill(code);
    await check(page).click();
    await expect(page.getByText(label)).toBeVisible();
    await expect(page.getByText(next, { exact: false })).toBeVisible();
    if (code === "SG-REFERRED-1") {
      await expect(page.getByText(/does not promise a response from anyone else/)).toBeVisible();
    }
  }
});

test("a reviewer's question can be answered once, and a retry reuses the same key", async ({
  page
}) => {
  const keys: string[] = [];

  page.on("request", (request) => {
    if (request.url().endsWith("/api/tracking/follow-up")) {
      keys.push(request.headers()["idempotency-key"] ?? "");
    }
  });
  await ready(page);
  await codeBox(page).fill("SG-FOLLOWUP-1");
  await check(page).click();
  await expect(page.getByText("Roughly when did you see this (fictional)?")).toBeVisible();
  await expect(page.getByText("You answered")).toBeVisible();

  await page.getByRole("button", { name: "Send answer" }).click();
  await expect(page.getByText("Type an answer, or choose to skip.")).toBeVisible();
  await page.getByLabel("Your answer").fill("Around noon, fictional.");
  await page.getByRole("button", { name: "Send answer" }).click();

  await expect(page.getByText("Your response was sent.")).toBeVisible();
  await expect(page.getByText("Waiting for your response")).toHaveCount(0);
  expect(keys).toHaveLength(1);
});

test("an answer that fails keeps the text and retries with the same key", async ({ page }) => {
  const keys: string[] = [];

  page.on("request", (request) => {
    if (request.url().endsWith("/api/tracking/follow-up")) {
      keys.push(request.headers()["idempotency-key"] ?? "");
    }
  });
  await ready(page);
  await codeBox(page).fill("SG-FOLLOWUP-2");
  await check(page).click();
  await page.getByLabel("Your answer").fill("Text __unavailable");
  await page.getByRole("button", { name: "Send answer" }).click();
  await expect(
    page
      .locator("[data-slot=track-failure]")
      .getByText("The service is unavailable right now. Try again shortly.")
  ).toBeVisible();
  await page.getByRole("button", { name: "Send answer" }).click();
  await expect(page.locator("[data-slot=track-failure]")).toBeVisible();

  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
  await expect(page.getByLabel("Your answer")).toHaveValue("Text __unavailable");
});

test("a handle lists reports without calling itself an account, and a wrong or missing handle look identical", async ({
  page
}) => {
  await ready(page);
  const handle = page.getByLabel("Handle", { exact: true }).first();
  const pass = page.getByLabel("Passphrase", { exact: true }).first();

  await handle.fill("wrong-handle");
  await pass.fill("alpha bravo charlie");
  await page.getByRole("button", { name: "List my reports" }).click();
  const wrong = await page.locator("[data-slot=handle-result]").innerText();

  await handle.fill("missing-handle");
  await pass.fill("something else");
  await page.getByRole("button", { name: "List my reports" }).click();
  await expect(
    page
      .locator("[data-slot=handle-result]")
      .getByText("Those details were not accepted. Check them and try again.")
  ).toBeVisible();
  expect(await page.locator("[data-slot=handle-result]").innerText()).toBe(wrong);

  await handle.fill("fictional-handle-001");
  await pass.fill("amber bridge candle");
  await page.getByRole("button", { name: "List my reports" }).click();
  await expect(
    page.locator("[data-slot=handle-result]").getByText("Status: Under review")
  ).toBeVisible();
  await expect(
    page.locator("[data-slot=handle-result]").getByText("Status: Received")
  ).toBeVisible();
  await expect(pass).toHaveValue("");
  expect(await storageAndCookies(page)).not.toContain("amber");
  expect(await page.content()).not.toMatch(/verified identity|your account/i);

  await handle.fill("empty-handle");
  await pass.fill("x");
  await page.getByRole("button", { name: "List my reports" }).click();
  await expect(
    page
      .locator("[data-slot=handle-result]")
      .getByText("No reports are linked to this handle right now.")
  ).toBeVisible();
});

test("pressing Enter in the code box checks it, and offline reports a network failure that can be retried", async ({
  page,
  context
}) => {
  await ready(page);
  await codeBox(page).fill(SECRET_CODE);
  await codeBox(page).press("Enter");
  await expect(page.getByText("Status: Under review")).toBeVisible();

  await page.getByRole("button", { name: "Clear and start again" }).first().click();
  await codeBox(page).fill(SECRET_CODE);
  await context.setOffline(true);
  await check(page).click();
  await expect(
    page
      .locator("[data-slot=track-result]")
      .getByText("Could not reach ShaidaGo. Check your connection and try again.")
  ).toBeVisible();
  await context.setOffline(false);
  await check(page).click();
  await expect(page.getByText("Status: Under review")).toBeVisible();
});

test("without JavaScript the status page says why nothing can be sent", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  await page.goto(TRACK);
  await expect(page.getByText("Checking a status needs JavaScript.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Check status" })).toBeDisabled();
  expect(page.url()).not.toContain("?");
  await context.close();
});

test("status and handle pages are never cached or indexed, and open in every language", async ({
  page
}) => {
  for (const path of ["/en/track", "/en/handle"]) {
    const response = await page.goto(path);

    expect(response?.headers()["cache-control"]).toContain("no-store");
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  }
  for (const locale of ["ha", "ig", "yo"]) {
    for (const route of ["track", "handle"]) {
      await page.goto(`/${locale}/${route}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(page.locator("html")).toHaveAttribute("lang", locale);
    }
  }
});

test.describe("handle creation and deletion", () => {
  test("a new handle is shown once, is not stored, and a refresh cannot bring it back", async ({
    page
  }) => {
    await ready(page, "/en/handle").catch(() => undefined);
    await page.goto("/en/handle");
    const create = page.getByRole("button", { name: "Create a handle" });

    await expect(create).toBeEnabled();
    await create.click();
    const created = page.locator("[data-slot=handle-created]");

    await expect(created).toBeVisible();
    const handle = (await page.locator("[data-slot=created-handle]").innerText()).trim();
    const passphrase = (await page.locator("[data-slot=created-passphrase]").innerText()).trim();

    expect(handle).toMatch(/^fictional-handle-\d{3}$/);
    await expect(created.getByText("These are shown once.")).toBeVisible();
    const stored = await storageAndCookies(page);

    expect(stored).not.toContain(handle);
    expect(stored).not.toContain(passphrase);
    expect(page.url()).not.toContain(handle);

    await page.reload();
    await expect(page.locator("[data-slot=handle-created]")).toHaveCount(0);
    expect(await page.content()).not.toContain(passphrase);
    await expect(page.getByText(/cannot be shown again/).first()).toBeVisible();

    await page.getByRole("button", { name: "Create a handle" }).click();
    expect((await page.locator("[data-slot=created-handle]").innerText()).trim()).not.toBe(handle);
  });

  test("copy and download happen only when asked, and the page can be cleared", async ({
    page,
    context,
    browserName
  }) => {
    await page.goto("/en/handle");
    await expect(page.getByRole("button", { name: "Create a handle" })).toBeEnabled();
    await page.getByRole("button", { name: "Create a handle" }).click();
    const handle = (await page.locator("[data-slot=created-handle]").innerText()).trim();

    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download as a text file" }).click();
    const file = await download;

    expect(file.suggestedFilename()).toBe("shaidago-reporter-handle.txt");
    expect(
      await (await import("node:fs/promises")).readFile((await file.path()) ?? "", "utf8")
    ).toContain(handle);
    if (browserName === "chromium") {
      await context.grantPermissions(["clipboard-read", "clipboard-write"]);
      await page.getByRole("button", { name: "Copy the handle and passphrase" }).click();
      await expect(page.getByText("Copied", { exact: true })).toBeVisible();
    }
    await page.getByRole("button", { name: "I have saved them. Clear this page" }).click();
    await expect(page.locator("[data-slot=handle-created]")).toHaveCount(0);
    expect(await page.content()).not.toContain(handle);
  });

  test("deleting explains that reports stay, needs confirmation, and treats wrong credentials generically", async ({
    page
  }) => {
    await page.goto("/en/handle");
    const submit = page.getByRole("button", { name: "Delete this handle" });

    await expect(submit).toBeEnabled();
    await expect(page.getByText(/does not delete the reports/)).toBeVisible();
    await page.getByLabel("Handle", { exact: true }).fill("wrong-handle");
    await page.locator("input[type=password]").fill("secret words");
    await submit.click();
    await expect(page.getByText("Tick the box to confirm.")).toBeVisible();

    await page.getByRole("checkbox", { name: /I understand the reports stay/ }).check();
    await submit.click();
    await expect(
      page
        .locator("[data-slot=delete-result]")
        .getByText("Those details were not accepted. Check them and try again.")
    ).toBeVisible();

    await page.getByLabel("Handle", { exact: true }).fill("fictional-handle-002");
    await submit.click();
    await expect(
      page
        .locator("[data-slot=delete-result]")
        .getByText("The handle was deleted. Your reports were not deleted.")
    ).toBeVisible();
    await expect(page.locator("input[type=password]")).toHaveValue("");
  });

  test("without JavaScript the handle page explains why it cannot act", async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();

    await page.goto("/en/handle");
    await expect(page.getByText("Creating or deleting a handle needs JavaScript.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Create a handle" })).toBeDisabled();
    await context.close();
  });
});
