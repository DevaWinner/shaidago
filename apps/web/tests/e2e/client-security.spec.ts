import { expect, test, type Page } from "@playwright/test";

import { signInAs } from "../support/reviewer-session";

const ORIGIN = "http://127.0.0.1:3100";
const REPORT = "0198f1a2-7b3c-4d4e-8f5a-000000000001";

const PUBLIC_ROUTES = [
  "/en",
  "/ha",
  "/en/projects",
  "/en/projects/synthetic-record-full",
  "/en/projects/synthetic-record-full/sources/00000000-0000-4000-8000-000000000002",
  "/en/trust",
  "/en/report/synthetic-record-full",
  "/en/track",
  "/en/handle",
  "/en/offline"
];
const REVIEWER_ROUTES = [
  "/en/reviewer/sign-in",
  "/en/reviewer/reports",
  `/en/reviewer/reports/${REPORT}`,
  `/en/reviewer/reports/${REPORT}?reveal=contact`
];

test("every kind of response carries the security headers, and HSTS never on local HTTP", async ({
  context,
  request
}) => {
  await signInAs(context, ORIGIN);
  for (const path of [
    "/en",
    "/en/report",
    "/en/reviewer/sign-in",
    "/api/tracking/lookup",
    "/_next/static/none.js",
    "/manifest.webmanifest"
  ]) {
    const response = path.startsWith("/api")
      ? await request.post(path, { data: {}, headers: { Origin: ORIGIN } })
      : await request.get(path);
    const headers = response.headers();

    expect(headers["content-security-policy"], path).toContain("default-src 'self'");
    expect(headers["content-security-policy"], path).toContain("frame-ancestors 'none'");
    expect(headers["content-security-policy"], path).toContain("object-src 'none'");
    expect(headers["content-security-policy"], path).toContain("form-action 'self'");
    expect(headers["content-security-policy"], path).not.toContain("http");
    expect(headers["x-frame-options"], path).toBe("DENY");
    expect(headers["x-content-type-options"], path).toBe("nosniff");
    expect(headers["referrer-policy"], path).toBe("same-origin");
    expect(headers["permissions-policy"], path).toContain("camera=()");
    expect(headers["cross-origin-opener-policy"], path).toBe("same-origin");
    expect(headers["strict-transport-security"], path).toBeUndefined();
  }
});

test("no page breaks the content security policy, and nothing is requested from another origin", async ({
  context,
  page
}) => {
  const violations: string[] = [];
  const foreign: string[] = [];

  await page.addInitScript(() => {
    (window as unknown as { __csp: string[] }).__csp = [];
    document.addEventListener("securitypolicyviolation", (event) => {
      (window as unknown as { __csp: string[] }).__csp.push(
        `${event.violatedDirective} ${event.blockedURI}`
      );
    });
  });
  page.on("request", (request) => {
    if (
      !request.url().startsWith(ORIGIN) &&
      !request.url().startsWith("data:") &&
      !request.url().startsWith("blob:")
    )
      foreign.push(request.url());
  });
  await signInAs(context, ORIGIN);
  for (const path of [...PUBLIC_ROUTES, ...REVIEWER_ROUTES]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    violations.push(
      ...(await page.evaluate(() => (window as unknown as { __csp?: string[] }).__csp ?? [])).map(
        (item) => `${path}: ${item}`
      )
    );
  }
  expect(violations).toEqual([]);
  expect(foreign).toEqual([]);
});

test("every external link opens safely and no page pulls a third-party script, font, or stylesheet", async ({
  context,
  page
}) => {
  await signInAs(context, ORIGIN);
  for (const path of [...PUBLIC_ROUTES, ...REVIEWER_ROUTES]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const audit = await page.evaluate((origin) => {
      const external = [...document.querySelectorAll<HTMLAnchorElement>("a[href^='http']")].filter(
        (link) => !link.href.startsWith(origin)
      );
      const resources = [
        ...document.querySelectorAll<HTMLElement>("script[src], link[href], img[src], iframe[src]")
      ]
        .map((node) => (node as HTMLScriptElement).src || (node as HTMLLinkElement).href)
        .filter((url) => url.startsWith("http") && !url.startsWith(origin));

      return {
        unsafe: external
          .filter((link) => !/noopener/.test(link.rel) || !/noreferrer/.test(link.rel))
          .map((link) => link.href),
        resources
      };
    }, ORIGIN);

    expect(audit.unsafe, path).toEqual([]);
    expect(audit.resources, path).toEqual([]);
  }
});

test("hostile text in a report, a note, a source excerpt, and a discovered page is shown as text and never runs", async ({
  context,
  page
}) => {
  const dialogs: string[] = [];

  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.dismiss();
  });
  await signInAs(context, ORIGIN);
  await page.goto(`/en/reviewer/reports/${REPORT}`);
  await expect(page.locator("[data-slot=report-description]")).toContainText(
    "<script>alert(1)</script>"
  );
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Optional public search terms").fill("");
  await page.getByRole("button", { name: "Prepare query for review" }).click();
  await page.getByLabel("Outbound query").waitFor();
  await page.getByRole("button", { name: "Approve and start search" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Approve and start" }).click();
  await expect(
    page.locator("[data-slot=discovery-run] [data-slot=discovery-source]").first()
  ).toBeVisible();
  await expect(page.locator("[data-slot=discovery-run]")).toContainText(
    "<script>alert(1)</script>"
  );
  await page.goto("/en/projects/synthetic-record-full");
  await page.waitForLoadState("networkidle");
  await page.goto(
    "/en/projects/synthetic-record-full/sources/00000000-0000-4000-8000-000000000002"
  );
  await page.waitForLoadState("networkidle");

  expect(dialogs).toEqual([]);
  expect(
    await page.evaluate(() => (window as unknown as { __xss?: unknown }).__xss)
  ).toBeUndefined();
  expect(
    await page
      .locator("script:not([src])")
      .evaluateAll((nodes) =>
        nodes.map((node) => node.textContent).filter((text) => /alert\(1\)/.test(text ?? ""))
      )
  ).toEqual([]);
});

test("the site cannot be framed by another origin", async ({ page }) => {
  await page.goto("about:blank");
  await page.setContent(`<iframe id="f" src="${ORIGIN}/en" width="600" height="400"></iframe>`);
  await page.waitForTimeout(1500);
  const frame = page.frames().find((item) => item !== page.mainFrame());
  const text = await frame?.evaluate(() => document.body?.innerText ?? "").catch(() => "");

  expect(text ?? "").not.toContain("ShaidaGo");
});

test("a page does not change with the request's host, language header, or a stray cookie, so a shared cache cannot be poisoned by one", async ({
  request
}) => {
  // The catalogue itself may change between requests (other tests move the mock), so the spoofed
  // response is compared with a plain one taken just before and just after it.
  const before = await (await request.get("/en/projects")).text();
  const spoofed = await request.get("/en/projects", {
    headers: {
      "X-Forwarded-Host": "evil.example",
      "X-Forwarded-Proto": "https",
      "Accept-Language": "yo",
      Cookie: "NEXT_LOCALE=ha"
    }
  });
  const body = await spoofed.text();

  const after = await (await request.get("/en/projects")).text();

  expect(body).not.toContain("evil.example");
  expect([before, after]).toContain(body);
  expect(spoofed.headers()["vary"] ?? "").not.toMatch(/cookie/i);
});

test("no page or API response contains a signed storage link or a credential", async ({
  context,
  page,
  request
}) => {
  await signInAs(context, ORIGIN);
  const pages = [...PUBLIC_ROUTES, ...REVIEWER_ROUTES];

  for (const path of pages) {
    await page.goto(path);
    const html = await page.content();

    expect(html, path).not.toMatch(/X-Amz-|Signature=|AWSAccessKeyId|sg_session|sg_csrf|Bearer /);
  }
  const file = await page.request.get(
    `/api/reviewer/reports/${REPORT}/evidence/0198f1a2-7b3c-4d4e-8f5a-a00000000001`
  );

  expect(file.headers()["location"]).toBeUndefined();
  expect(file.headers()["content-type"]).toBeDefined();
  expect((await request.get("/en")).headers()["set-cookie"] ?? "").not.toMatch(/sg_session/);
});

async function noPrivateResidue(page: Page): Promise<void> {
  expect(await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }))).toBe(
    "{}"
  );
  expect(await page.evaluate(() => document.cookie)).not.toMatch(/sg_session|sg_csrf|SG-FICTIONAL/);
  expect(await page.evaluate(async () => (await window.indexedDB.databases?.()) ?? [])).toEqual([]);
}

test("after tracking and reviewer flows, browser storage, IndexedDB, cookies, and the address hold nothing private", async ({
  context,
  page
}) => {
  await page.goto("/en/track");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Tracking code", { exact: true }).fill("SG-FICTIONAL-0001-UNDERREVIEW");
  await page.getByRole("button", { name: "Check status" }).click();
  await expect(page.getByText("Status: Under review")).toBeVisible();
  await noPrivateResidue(page);
  expect(page.url()).not.toContain("FICTIONAL");

  await signInAs(context, ORIGIN);
  await page.goto(`/en/reviewer/reports/${REPORT}?reveal=contact`);
  await noPrivateResidue(page);
  expect(page.url()).not.toContain("fictional-contact");
  const history = await page.evaluate(() => window.history.length);

  expect(history).toBeGreaterThan(0);
});
