import { expect, test } from "@playwright/test";

test("liveness and readiness answer unprefixed, uncached, and without touching the private API", async ({
  request
}) => {
  for (const [path, status] of [
    ["/health/live", "live"],
    ["/health/ready", "ready"]
  ] as const) {
    const response = await request.get(path, { maxRedirects: 0 });

    expect(response.status(), path).toBe(200);
    expect(response.headers()["cache-control"], path).toContain("no-store");
    expect(await response.json()).toEqual({ status });
  }
});

test("the health routes reveal no configuration value", async ({ request }) => {
  const text =
    (await (await request.get("/health/ready")).text()) +
    (await (await request.get("/health/live")).text());

  expect(text).not.toMatch(/http|credential|key|127\.0\.0\.1|shaida-go/i);
});
