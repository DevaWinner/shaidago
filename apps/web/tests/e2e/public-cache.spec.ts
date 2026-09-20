import { expect, test } from "@playwright/test";

const MOCK = "http://127.0.0.1:3200";

async function upstreamCalls(request: import("@playwright/test").APIRequestContext, query: string) {
  const stats = (await (await request.get(`${MOCK}/__stats`)).json()) as Record<string, number>;

  return stats[`/v1/projects?limit=12&q=${query}`] ?? 0;
}

test("identical public reads are fetched once, and each language and each filter set is its own cache entry", async ({
  page,
  request
}) => {
  const query = `cache-probe-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const visit = (path: string) => page.goto(path);

  expect(await upstreamCalls(request, query)).toBe(0);

  await visit(`/en/projects?q=${query}`);
  expect(await upstreamCalls(request, query)).toBe(1);
  await visit(`/en/projects?q=${query}`);
  await visit(`/en/projects?q=${query}`);
  // Served from the cache: the API was not asked again.
  expect(await upstreamCalls(request, query)).toBe(1);

  // A different language asks the API separately (the text it returns differs by locale).
  await visit(`/ha/projects?q=${query}`);
  expect(await upstreamCalls(request, query)).toBe(2);
  await visit(`/ha/projects?q=${query}`);
  expect(await upstreamCalls(request, query)).toBe(2);

  // A different filter set is a different entry.
  await visit(`/en/projects?q=${query}&category=health`);
  const stats = (await (await request.get(`${MOCK}/__stats`)).json()) as Record<string, number>;
  expect(stats[`/v1/projects?limit=12&q=${query}&category=health`]).toBe(1);
});

test("a cached page never keeps another visitor's private data, because none is ever fetched by a public page", async ({
  page,
  request
}) => {
  await request.post(`${MOCK}/__stats`);
  await page.goto("/en/projects");
  await page.goto("/en");

  const stats = (await (await request.get(`${MOCK}/__stats`)).json()) as Record<string, number>;
  const paths = Object.keys(stats).map((key) => key.split("?")[0]);

  // Public pages only ever call the public catalogue endpoints (list, localities, record, source).
  const isPublic = (path: string): boolean => {
    const parts = path.split("/").filter(Boolean);

    return (
      parts[0] === "v1" &&
      ((parts.length === 2 && ["localities", "projects"].includes(parts[1] ?? "")) ||
        (parts.length === 3 && parts[1] === "projects") ||
        (parts.length === 4 && parts[1] === "projects" && parts[3] === "questions") ||
        (parts.length === 5 && parts[1] === "projects" && parts[3] === "sources"))
    );
  };
  for (const path of paths) {
    expect(isPublic(path ?? ""), path).toBe(true);
  }
});

test("an outage is never cached: the next visit asks the API again", async ({ page, request }) => {
  const failing = "/v1/projects?limit=12&q=__unavailable";
  const before =
    ((await (await request.get(`${MOCK}/__stats`)).json()) as Record<string, number>)[failing] ?? 0;

  await page.goto("/en/projects?q=__unavailable");
  const afterOne =
    ((await (await request.get(`${MOCK}/__stats`)).json()) as Record<string, number>)[failing] ?? 0;
  await page.goto("/en/projects?q=__unavailable");
  const afterTwo =
    ((await (await request.get(`${MOCK}/__stats`)).json()) as Record<string, number>)[failing] ?? 0;

  expect(afterOne).toBeGreaterThan(before);
  expect(afterTwo).toBeGreaterThan(afterOne);
});
