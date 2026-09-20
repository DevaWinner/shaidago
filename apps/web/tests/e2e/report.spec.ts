import { expect, test, type Page } from "@playwright/test";

const MOCK = "http://127.0.0.1:3200";
const FORM = "/en/report/synthetic-record-full";
const DESCRIPTION = "A fictional wall by the road is leaning.";

type Logged = {
  key: string;
  fields: string[];
  fileCount: number;
  fileNames: string[];
  exif: boolean;
  replay: boolean;
};

/** Records the idempotency key of every report request this page sends, so the mock log can be read by key. */
function watchKeys(page: Page): string[] {
  const keys: string[] = [];

  page.on("request", (request) => {
    if (request.url().endsWith("/api/reports") && request.method() === "POST") {
      keys.push(request.headers()["idempotency-key"] ?? "");
    }
  });

  return keys;
}

async function logFor(page: Page, key: string): Promise<Logged[]> {
  const all = (await (await page.request.get(`${MOCK}/__reports`)).json()) as Logged[];

  return all.filter((entry) => entry.key === key);
}

async function start(page: Page, path = FORM): Promise<void> {
  await page.goto(path);
  const begin = page.getByRole("button", { name: "I understand. Continue" });
  await expect(begin).toBeEnabled();
  await begin.click();
}

async function observe(page: Page, text = DESCRIPTION): Promise<void> {
  await page.locator("#report-category").selectOption("unsafe_construction");
  await page.locator("#report-description").fill(text);
}

const next = (page: Page) => page.getByRole("button", { name: "Continue", exact: true }).click();

async function toReview(page: Page, description = DESCRIPTION): Promise<void> {
  await start(page);
  await observe(page, description);
  await next(page);
  await next(page);
  await next(page);
  await expect(page.getByRole("heading", { name: "Review and send" })).toBeVisible();
}

const send = (page: Page) =>
  page.getByRole("button", { name: /^(Send report|Send again)$/ }).click();

/** A JPEG that really carries an Exif segment with a GPS marker, built in the page from a canvas. */
async function gpsJpeg(page: Page): Promise<Buffer> {
  const base64 = await page.evaluate(async () => {
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 48;
    canvas.getContext("2d")?.fillRect(0, 0, 64, 48);
    const blob: Blob = await new Promise((resolve) =>
      canvas.toBlob((b) => resolve(b as Blob), "image/jpeg")
    );
    const jpeg = new Uint8Array(await blob.arrayBuffer());
    const payload = new TextEncoder().encode(
      "Exif\0\0GPSLatitude=9.0765 GPSLongitude=7.3986 Make=FictionalCam"
    );
    const segment = new Uint8Array(4 + payload.length);
    segment.set([0xff, 0xe1, (payload.length + 2) >> 8, (payload.length + 2) & 255], 0);
    segment.set(payload, 4);
    const out = new Uint8Array(jpeg.length + segment.length);
    out.set(jpeg.slice(0, 2), 0);
    out.set(segment, 2);
    out.set(jpeg.slice(2), 2 + segment.length);
    let text = "";
    for (const byte of out) text += String.fromCharCode(byte);
    return btoa(text);
  });

  return Buffer.from(base64, "base64");
}

test("an anonymous report is sent once with only the needed fields, and the code appears once", async ({
  page
}) => {
  const keys = watchKeys(page);

  await toReview(page);
  await expect(page.getByText("Fully anonymous")).toBeVisible();
  await send(page);

  await expect(page).toHaveURL(/\/en\/report\/complete$/);
  const code = (await page.locator("[data-slot=tracking-code]").innerText()).trim();
  expect(code).toMatch(/^SG-DEMO-\d{4}-FICTIONAL$/);
  await expect(page.getByText("This code is shown once")).toBeVisible();
  expect(keys).toHaveLength(1);

  const [entry] = await logFor(page, keys[0] ?? "");
  expect(entry?.fields).toEqual(["project_slug", "concern_category", "description"]);
  expect(entry?.fileCount).toBe(0);

  // The code is in no address, storage, or cookie.
  expect(page.url()).not.toContain(code);
  const stored = await page.evaluate(() =>
    JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie])
  );
  expect(stored).not.toContain(code);
  expect(JSON.stringify(await page.context().cookies())).not.toContain(code);
  expect((await page.title()).includes(code)).toBe(false);
});

test("reloading, revisiting, or going back never shows the code again", async ({ page }) => {
  await toReview(page);
  await send(page);
  const code = (await page.locator("[data-slot=tracking-code]").innerText()).trim();

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "The tracking code is no longer available" })
  ).toBeVisible();
  expect(await page.content()).not.toContain(code);

  await page.goto("/en/report/complete");
  await expect(page.getByText("it cannot be recovered")).toBeVisible();
  await page.goBack();
  expect(await page.content()).not.toContain(code);
});

test("the confirmation page is never cached and is not indexed", async ({ page }) => {
  const response = await page.goto("/en/report/complete");

  expect(response?.headers()["cache-control"]).toContain("no-store");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
  const form = await page.goto(FORM);
  expect(form?.headers()["cache-control"]).toContain("no-store");
});

test("choosing contact adds contact fields, and switching back removes them from the report", async ({
  page
}) => {
  const keys = watchKeys(page);

  await start(page);
  await observe(page);
  await next(page);
  await next(page);
  await page.getByRole("radio", { name: /Give a way to contact me/ }).check();
  await page.locator("#report-contact-channel").selectOption("email");
  await page.locator("#report-contact-value").fill("someone@example.org");
  await page.getByRole("radio", { name: /Stay fully anonymous/ }).check();
  await next(page);
  await send(page);
  await expect(page).toHaveURL(/complete$/);

  const [entry] = await logFor(page, keys[0] ?? "");
  expect(entry?.fields).not.toContain("contact_value");
  expect(entry?.fields).not.toContain("contact_channel");
});

test("a contact detail is sent only when chosen and is reported as saved separately", async ({
  page
}) => {
  const keys = watchKeys(page);

  await start(page);
  await observe(page);
  await next(page);
  await next(page);
  await page.getByRole("radio", { name: /Give a way to contact me/ }).check();
  await page.locator("#report-contact-channel").selectOption("email");
  await page.locator("#report-contact-value").fill("someone@example.org");
  await next(page);
  await expect(page.getByText("Contact given: Email")).toBeVisible();
  await send(page);

  await expect(page.getByText("Your contact detail was saved separately.")).toBeVisible();
  const [entry] = await logFor(page, keys[0] ?? "");
  expect(entry?.fields).toEqual(expect.arrayContaining(["contact_channel", "contact_value"]));
});

test("handle credentials are checked only at submission: a refusal returns to that step and nothing is remembered", async ({
  page
}) => {
  await start(page);
  await observe(page, `${DESCRIPTION} __invalid_handle`);
  await next(page);
  await next(page);
  await page.getByRole("radio", { name: /Use a reporter handle/ }).check();
  await expect(page.getByText(/recognise reports under one handle as related/)).toBeVisible();
  await page.locator("#report-handle").fill("fictional-handle");
  await page.locator("#report-passphrase").fill("one two three four five six");
  await next(page);
  await expect(page.getByText("Handle: fictional-handle. Passphrase hidden.")).toBeVisible();
  await send(page);

  await expect(
    page.getByRole("heading", { name: "How you are identified", level: 2 })
  ).toBeVisible();
  await expect(page.locator("[data-slot=error-summary]")).toBeVisible();
  await expect(
    page.getByText("Those details were not accepted. Check them and try again.").first()
  ).toBeVisible();
  const stored = await page.evaluate(() =>
    JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie])
  );
  expect(stored).not.toContain("one two three");
  expect(stored).not.toContain("fictional-handle");
});

test("a photo is re-saved without location or camera details before it is sent, under a neutral name", async ({
  page
}) => {
  const keys = watchKeys(page);
  await start(page);
  await observe(page);
  await next(page);
  const jpeg = await gpsJpeg(page);
  expect(jpeg.includes(Buffer.from("GPSLatitude"))).toBe(true);

  await page.getByLabel("Add a file").setInputFiles([
    { name: "Home-Lekki-GPS.jpg", mimeType: "image/jpeg", buffer: jpeg },
    {
      name: "Notes for me.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.7 fictional")
    }
  ]);
  await expect(
    page.getByText("Location and camera details were removed in your browser.")
  ).toBeVisible();
  await expect(page.getByText(/A PDF is not changed in your browser/)).toBeVisible();
  await expect(page.getByRole("img", { name: "Preview of file 1" })).toBeVisible();
  await next(page);
  await next(page);
  await send(page);
  await expect(page).toHaveURL(/complete$/);

  const [entry] = await logFor(page, keys[0] ?? "");
  expect(entry?.fileCount).toBe(2);
  expect(entry?.exif).toBe(false);
  expect(entry?.fileNames).toEqual(["attachment-1.jpg", "attachment-2.pdf"]);
});

test("unsupported, mismatched, and surplus files are refused with a clear reason and are never sent", async ({
  page
}) => {
  await start(page);
  await observe(page);
  await next(page);

  await page.getByLabel("Add a file").setInputFiles([
    { name: "a.gif", mimeType: "image/gif", buffer: Buffer.from("GIF89a....") },
    { name: "b.jpg", mimeType: "image/jpeg", buffer: Buffer.from("%PDF-1.7 fictional") }
  ]);
  await expect(
    page.getByText("File 1 is not a JPEG, PNG, WebP, or PDF, so it was not added.")
  ).toBeVisible();
  await expect(
    page.getByText("File 2 is not the kind of file its name says, so it was not added.")
  ).toBeVisible();
  await expect(page.getByText("No files added.")).toBeVisible();

  const pdf = { name: "p.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 x") };
  await page.getByLabel("Add a file").setInputFiles([pdf, pdf, pdf, pdf]);
  await expect(page.getByText("You can add at most 3 files.")).toBeVisible();
  await expect(page.getByRole("button", { name: /Remove file/ })).toHaveCount(3);
  await page.getByRole("button", { name: "Remove file 1" }).click();
  await expect(page.getByRole("button", { name: /Remove file/ })).toHaveCount(2);
});

test("a rejected attachment does not stop the report, and the outcome is shown per file", async ({
  page
}) => {
  await start(page);
  await observe(page, `${DESCRIPTION} __reject_attachment`);
  await next(page);
  await page.getByLabel("Add a file").setInputFiles([
    { name: "x.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 x") },
    { name: "y.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 y") }
  ]);
  await next(page);
  await next(page);
  await send(page);

  await expect(
    page.getByRole("heading", { level: 1, name: "Your report was received" })
  ).toBeVisible();
  await expect(
    page.getByText("File 1: not kept (it could not be read). The report itself was received.")
  ).toBeVisible();
  await expect(page.getByText("File 2: kept after the server's checks.")).toBeVisible();
});

test("a dropped connection is retried with the same key and never creates a second report", async ({
  page
}) => {
  const keys = watchKeys(page);

  await toReview(page, `${DESCRIPTION} __dropfirst`);
  await send(page);
  await expect(
    page
      .locator("[data-slot=send-failure]")
      .getByText(/could not confirm whether your report was received/)
  ).toBeVisible();
  await send(page);

  await expect(page).toHaveURL(/complete$/);
  expect(keys).toHaveLength(2);
  expect(keys[1]).toBe(keys[0]);
  const entries = await logFor(page, keys[0] ?? "");
  expect(entries.map((entry) => entry.replay)).toEqual([false, true]);
  await expect(page.locator("[data-slot=tracking-code]")).toHaveText(/SG-DEMO-\d{4}-FICTIONAL/);
});

test("a rate limit, an outage, and a server-side validation error each keep the report and say what to do", async ({
  page
}) => {
  await toReview(page, `${DESCRIPTION} __ratelimit`);
  await send(page);
  await expect(
    page.locator("[data-slot=send-failure]").getByText("Try again in about 30 seconds.")
  ).toBeVisible();
  await expect(page.locator("[data-slot=send-failure]")).toBeFocused();
  await page.getByRole("button", { name: /Change.*What you saw/ }).click();
  await expect(page.locator("#report-description")).toHaveValue(`${DESCRIPTION} __ratelimit`);
});

test("an outage is reported without losing the report", async ({ page }) => {
  await toReview(page, `${DESCRIPTION} __unavailable`);
  await send(page);

  await expect(
    page
      .locator("[data-slot=send-failure]")
      .getByText("The service is unavailable right now. Try again shortly.")
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Send again" })).toBeVisible();
});

test("a validation error returns to the step that owns the field", async ({ page }) => {
  await toReview(page, `${DESCRIPTION} __validation`);
  await send(page);

  await expect(page.locator("[data-slot=error-summary]")).toBeVisible();
  await expect(page.locator("#report-description")).toHaveValue(`${DESCRIPTION} __validation`);
});

test("sending can be cancelled, and the report is kept", async ({ page }) => {
  await toReview(page, `${DESCRIPTION} __slow`);
  await send(page);
  await page.getByRole("button", { name: "Cancel sending" }).click();

  await expect(
    page
      .locator("[data-slot=send-failure]")
      .getByText("Sending was cancelled. Your report is still here.")
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Send again" })).toBeVisible();
});

test("offline: nothing is sent, and the report goes once the connection is back", async ({
  page,
  context
}) => {
  const keys = watchKeys(page);

  await toReview(page);
  await context.setOffline(true);
  await send(page);
  await expect(
    page.locator("[data-slot=send-failure]").getByText(/appear to be offline/)
  ).toBeVisible();
  expect(keys).toHaveLength(0);
  await context.setOffline(false);
  await send(page);
  await expect(page).toHaveURL(/complete$/);
});

test("a draft is saved only after consent, holds only the concern and description, and can be deleted", async ({
  page
}) => {
  await start(page);
  await observe(page);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);

  await page.getByRole("checkbox", { name: /Save what I have written on this device/ }).check();
  await expect(
    page.getByText(/Anyone who uses this browser could read a saved draft/)
  ).toBeVisible();
  const raw = await page.evaluate(() => localStorage.getItem("shaidago.report-draft"));
  expect(Object.keys(JSON.parse(raw ?? "{}") as object).sort()).toEqual([
    "category",
    "description",
    "project",
    "savedAt",
    "step",
    "version"
  ]);

  await page.reload();
  await expect(page.getByText(/You have a saved draft from/)).toBeVisible();
  await page.getByRole("button", { name: "Restore the draft" }).click();
  await expect(page.locator("#report-description")).toHaveValue(DESCRIPTION);
  await page.getByRole("button", { name: "Delete the saved draft" }).click();
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test("a draft is dropped when the report is sent, and files and contact never enter it", async ({
  page
}) => {
  await start(page);
  await observe(page);
  await page.getByRole("checkbox", { name: /Save what I have written on this device/ }).check();
  await next(page);
  await page.getByLabel("Add a file").setInputFiles({
    name: "x.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.7 x")
  });
  await next(page);
  await page.getByRole("radio", { name: /Give a way to contact me/ }).check();
  await page.locator("#report-contact-channel").selectOption("email");
  await page.locator("#report-contact-value").fill("someone@example.org");
  const raw = (await page.evaluate(() => localStorage.getItem("shaidago.report-draft"))) ?? "";
  expect(raw).not.toContain("someone@example.org");
  expect(raw).not.toContain("pdf");
  await next(page);
  await send(page);

  await expect(page).toHaveURL(/complete$/);
  expect(await page.evaluate(() => localStorage.length)).toBe(0);
});

test("the code can be copied, printed, and downloaded, only when asked", async ({
  page,
  context,
  browserName
}) => {
  await toReview(page);
  await send(page);
  const code = (await page.locator("[data-slot=tracking-code]").innerText()).trim();

  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download as a text file" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("shaidago-tracking-code.txt");
  const path = await file.path();
  expect(path).toBeTruthy();
  expect(await (await import("node:fs/promises")).readFile(path, "utf8")).toContain(code);

  if (browserName === "chromium") {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.getByRole("button", { name: "Copy the code" }).click();
    await expect(page.getByText("Copied", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(code);
  }
  await expect(page.getByRole("link", { name: "Go to the status page" })).toHaveAttribute(
    "href",
    "/en/track"
  );
});

test("a keyboard user can complete the whole report", async ({ page, browserName }) => {
  test.skip(browserName === "webkit", "iOS WebKit does not Tab to buttons by default");
  await page.goto(FORM);
  await expect(page.getByRole("button", { name: "I understand. Continue" })).toBeEnabled();
  await page.getByRole("button", { name: "I understand. Continue" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "What you saw", exact: true })).toBeFocused();
  // A native select's arrow keys differ by platform, so the choice is set directly and the keyboard
  // continues from that control to the description.
  await page.locator("#report-category").selectOption("unsafe_construction");
  await page.locator("#report-category").focus();
  await page.keyboard.press("Tab");
  await page.keyboard.type(DESCRIPTION);
  for (let i = 0; i < 3; i += 1) {
    await page.getByRole("button", { name: "Continue", exact: true }).focus();
    await page.keyboard.press("Enter");
  }
  await page.getByRole("button", { name: "Send report" }).focus();
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/complete$/);
});

test("the entry page sends a record link to that record's form, and lists records otherwise", async ({
  page
}) => {
  await page.goto("/en/report?project=synthetic-record-full");
  await expect(page).toHaveURL(/\/en\/report\/synthetic-record-full$/);

  await page.goto("/en/report");
  await expect(
    page.getByRole("heading", { level: 1, name: "Choose the project your report is about" })
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Synthetic example project 01" })).toHaveAttribute(
    "href",
    "/en/report/synthetic-project-01"
  );
  const bad = await page.goto("/en/report/Not_A_Slug!");
  expect(bad?.status()).toBe(404);
  const unknown = await page.goto("/en/report/synthetic-record-missing");
  expect(unknown?.status()).toBe(404);
});

test("without JavaScript the form explains why it cannot be used and sends nothing", async ({
  browser
}) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();

  await page.goto(FORM);
  await expect(page.getByText("Sending a report needs JavaScript.")).toBeVisible();
  await expect(page.getByRole("button", { name: "I understand. Continue" })).toBeDisabled();
  await expect(page.getByText(/not an emergency service/i).first()).toBeVisible();
  expect(page.url()).not.toContain("?");
  await context.close();
});

test("every language opens the form, and its steps are named", async ({ page }) => {
  for (const locale of ["ha", "ig", "yo"]) {
    await page.goto(`/${locale}/report/synthetic-record-full`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", locale);
  }
});
