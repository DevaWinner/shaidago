import { expect, test, type Page } from "@playwright/test";

const RECORD = "/en/projects/saburi-i-and-ii-access-road";
const FIXTURE = RECORD; // the synthetic fixture record was removed from staging
const REVIEWER = process.env["HOSTED_REVIEWER"];
const PASSWORD = process.env["HOSTED_REVIEWER_PASSWORD"];

async function residue(page: Page): Promise<string> {
  return (
    (await page.evaluate(() =>
      JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie])
    )) + page.url()
  );
}

test("the hosted routes carry the production headers, revalidated public pages, and no-store private ones", async ({
  request
}) => {
  const pub = (await request.get("/en")).headers();

  expect(pub["content-security-policy"]).toContain("default-src 'self'");
  expect(pub["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(pub["strict-transport-security"]).toContain("max-age=31536000");
  expect(pub["x-frame-options"]).toBe("DENY");
  expect(pub["x-content-type-options"]).toBe("nosniff");
  expect(pub["referrer-policy"]).toBe("same-origin");
  expect(pub["cache-control"]).toBe("public, max-age=0, must-revalidate");
  for (const path of ["/en/track", "/en/report", "/en/reviewer/sign-in", "/en/handle"]) {
    expect((await request.get(path)).headers()["cache-control"], path).toMatch(/no-store/);
  }
  const worker = (await request.get("/sw.js")).headers();

  expect(worker["cache-control"]).toContain("no-cache");
  expect(worker["service-worker-allowed"]).toBe("/");
  expect(await (await request.get("/health/live")).json()).toEqual({ status: "live" });
  expect(await (await request.get("/health/ready")).json()).toEqual({ status: "ready" });
});

test("the private API is not reachable from the browser or named in anything served", async ({
  page,
  request
}) => {
  await page.goto("/en/projects");
  await page.waitForLoadState("networkidle");
  const html = await page.content();
  const scripts = await page.evaluate(() =>
    [...document.querySelectorAll("script[src]")].map((node) => (node as HTMLScriptElement).src)
  );
  let text = html;

  for (const src of scripts) text += await (await request.get(src)).text();
  expect(text).not.toMatch(
    /railway\.internal|api\.railway|INTERNAL_WEB_CREDENTIAL|CLIENT_HMAC_KEY/
  );
  const direct = await request
    .get("http://api.railway.internal:8080/health/live", { timeout: 8000 })
    .then(
      () => "reachable",
      () => "unreachable"
    );

  expect(direct).toBe("unreachable");
});

for (const locale of ["en", "ha", "ig", "yo"] as const) {
  test(`${locale}: the landing, directory, and a cited record open with real data`, async ({
    page
  }) => {
    await page.goto(`/${locale}`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.goto(`/${locale}/projects`);
    await expect(
      page.locator("a[href*='/projects/saburi-i-and-ii-access-road']").first()
    ).toBeVisible();
    await page.goto(`/${locale}/projects/saburi-i-and-ii-access-road`);
    await expect(page.locator("[data-slot=claim]").first()).toBeVisible();
    await expect(page.locator("[data-slot=citation-trigger]").first()).toBeVisible();
    await page.setViewportSize({ width: 360, height: 740 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      )
    ).toBeLessThanOrEqual(0);
  });
}

test("a cited statement opens its source page, and the source page keeps the exact passage", async ({
  page
}) => {
  await page.goto(RECORD);
  await page.locator("[data-slot=citation-trigger]").first().click();
  await page.getByRole("link", { name: "Open the source page" }).first().click();
  await expect(page).toHaveURL(/\/sources\/[0-9a-f-]{36}$/);
  await expect(page.locator("blockquote, [data-slot=citation-entry]").first()).toBeVisible();
});

test("a question is answered from the record or refused, never guessed", async ({ page }) => {
  await page.goto(FIXTURE);
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Your question").fill("What was the contract value?");
  await page.getByRole("button", { name: "Ask the sources" }).click();
  const result = page.locator("[data-slot=question-result]");

  await expect(result).toBeVisible({ timeout: 30000 });
  await expect(result).toContainText(
    /Written by an AI from the approved sources|The approved sources do not answer this/
  );
});

test("public Source Scout ends in a stated state, and any result stays labelled unreviewed", async ({
  page
}) => {
  await page.goto(FIXTURE);
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Find public information" }).click();
  const panel = page.locator("[data-slot=project-discovery]");

  // Recorded replays exist only for the synthetic fixture, so a real record may finish with no
  // results; what must hold is a stated, non-looping end state and the label on anything shown.
  await expect(panel).toContainText(
    /Search completed|not available|could not|Waiting for review|Cancelled|Failed/i,
    { timeout: 40000 }
  );
  for (const card of await panel.locator("[data-slot=discovery-source]").all()) {
    await expect(card).toContainText("discovered — not yet reviewed");
  }
});

test("a fictional report is accepted with a one-time code, tracked without private text, and never shown again", async ({
  page
}) => {
  const canary = `Fictional gate check ${Date.now()} at the fictional site.`;

  await page.goto("/en/report/saburi-i-and-ii-access-road");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "I understand. Continue" }).click();
  await page.locator("#report-category").selectOption("unsafe_construction");
  await page.locator("#report-description").fill(canary);
  for (let step = 0; step < 3; step += 1)
    await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: /^(Send report|Send again)$/ }).click();
  await expect(page).toHaveURL(/\/en\/report\/complete$/, { timeout: 60000 });
  const code = (await page.locator("[data-slot=tracking-code]").innerText()).trim();

  expect(code.length).toBeGreaterThan(8);
  expect(await residue(page)).not.toContain(code);
  await page.goto("/en/track");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Tracking code", { exact: true }).fill(code);
  await page.getByRole("button", { name: "Check status" }).click();
  await expect(page.locator("[data-slot=track-result]")).toContainText("Status:", {
    timeout: 20000
  });
  expect(await page.content()).not.toContain(canary);
  await page.goto("/en/report/complete");
  await expect(
    page.getByRole("heading", { name: "The tracking code is no longer available" })
  ).toBeVisible();
  await page.goto("/en/track");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Tracking code", { exact: true }).fill("SG-NOT-A-REAL-CODE");
  await page.getByRole("button", { name: "Check status" }).click();
  await expect(
    page.locator("[data-slot=track-result], [data-slot=track-failure]").first()
  ).toBeVisible();
});

test("a saved public record opens offline with its saved time, and low-data mode keeps the actions", async ({
  context,
  page
}, info) => {
  test.skip(
    info.project.name !== "chromium-desktop",
    "Playwright WebKit cannot navigate offline with a service worker"
  );
  await page.goto("/en");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.goto(RECORD);
  await page.waitForLoadState("networkidle");
  await context.setOffline(true);
  await page.goto(RECORD);
  await expect(page.locator("[data-slot=offline-banner]")).toContainText("saved copy from");
  await expect(page.locator("[data-slot=claim]").first()).toBeVisible();
  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await page
    .locator("[data-slot=low-data]")
    .getByRole("button", { name: "Turn on low-data mode" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-low-data", "true");
  await page.goto("/en/projects");
  await expect(page.locator("form[role=search]")).toBeVisible();
});

test("no private route is stored by the hosted service worker", async ({ page }) => {
  await page.goto("/en");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  for (const path of ["/en/track", "/en/report", "/en/reviewer/sign-in", RECORD])
    await page.goto(path);
  const stored = await page.evaluate(async () => {
    const urls: string[] = [];

    for (const name of await caches.keys())
      for (const request of await (await caches.open(name)).keys())
        urls.push(new URL(request.url).pathname);

    return urls;
  });

  expect(stored.filter((path) => /\/(api|report|track|handle|reviewer)(\/|$)/.test(path))).toEqual(
    []
  );
});

test.describe("reviewer steps (need HOSTED_REVIEWER and HOSTED_REVIEWER_PASSWORD)", () => {
  test.skip(
    REVIEWER === undefined || PASSWORD === undefined,
    "no hosted reviewer credential supplied"
  );

  test("sign in, see the queue without report text, open a report, and sign out to a dead session", async ({
    page
  }) => {
    await page.goto("/en/reviewer/sign-in");
    await page.waitForLoadState("networkidle");
    await page.getByLabel(/^Reviewer identifier/).fill(REVIEWER ?? "");
    await page.getByLabel(/^Password/).fill(PASSWORD ?? "");
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL("**/en/reviewer/reports");
    await expect(page.locator("[data-slot=queue-item]").first()).toBeVisible();
    expect(await page.content()).not.toContain("Fictional gate check");
    await page.locator("[data-slot=queue-item]").first().getByRole("link").click();
    await expect(page.getByRole("heading", { level: 1, name: "Report" })).toBeVisible();
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/sign-in\?reason=signed_out/);
    await page.goBack();
    await expect(page).toHaveURL(/sign-in/);
  });
});
