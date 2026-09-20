import { createServer } from "node:http";

/**
 * A fictional stand-in for the two public catalogue endpoints, used only by the browser test
 * servers. Everything it returns is synthetic and labelled so. It checks the internal bearer
 * credential like the real API, applies the real filters and opaque cursors, and exposes test-only
 * controls (`/__mode`, `/__stats`) on the same port.
 */

const port = Number(process.env.MOCK_API_PORT ?? 3199);
const credential = process.env.INTERNAL_WEB_CREDENTIAL_CURRENT ?? "";

const CATEGORIES = [
  "health",
  "education",
  "water_sanitation",
  "roads_public_works",
  "other_public_service"
];
const STATUSES = [
  "unknown",
  "planned",
  "procurement",
  "in_progress",
  "on_hold",
  "completed",
  "cancelled"
];
const VERIFICATIONS = [
  "awaiting_verification",
  "verified_official",
  "corroborated",
  "community_reviewed",
  "disputed",
  "outdated"
];

const LOCALITIES = [
  {
    slug: "abuja",
    name: "Synthetic State",
    kind: "state",
    parent_slug: null,
    enabled_locales: ["en", "ha", "ig", "yo"]
  },
  {
    slug: "amac",
    name: "Synthetic Area Council A",
    kind: "area_council",
    parent_slug: "abuja",
    enabled_locales: ["en", "ha", "ig", "yo"]
  },
  {
    slug: "bwari",
    name: "Synthetic Area Council B",
    kind: "area_council",
    parent_slug: "abuja",
    enabled_locales: ["en", "ha", "ig", "yo"]
  }
];

const day = 24 * 60 * 60 * 1000;
const iso = (offsetDays) => new Date(Date.now() - offsetDays * day).toISOString().slice(0, 10);

function makeProjects(count) {
  return Array.from({ length: count }, (_, index) => {
    const number = String(index + 1).padStart(2, "0");

    return {
      slug: `synthetic-project-${number}`,
      category: CATEGORIES[index % CATEGORIES.length],
      public_status: STATUSES[index % STATUSES.length],
      locality_slug: index % 2 === 0 ? "amac" : "bwari",
      // One never checked, one checked long ago, the rest recently.
      last_checked_on: index === 3 ? null : index === 5 ? iso(200) : iso(index),
      updated_at: `${iso(index)}T09:00:00Z`,
      verification: VERIFICATIONS[index % VERIFICATIONS.length],
      title: `Synthetic example project ${number}`,
      summary: `A fictional record used for testing, number ${number}. It is not a real project.`
    };
  });
}

let mode = "ok";
let projects = makeProjects(30);
const stats = {};

function problem(response, status, code, extraHeaders = {}) {
  response.writeHead(status, {
    "Content-Type": "application/problem+json",
    "Cache-Control": "no-store",
    ...extraHeaders
  });
  response.end(
    JSON.stringify({
      type: "about:blank",
      title: "Fictional problem",
      status,
      code,
      detail: "synthetic detail that must never be shown",
      request_id: "0198f1a2-7b3c-4d4e-8f5a-123456789abc"
    })
  );
}

function json(response, body, locale) {
  response.writeHead(200, {
    "Content-Type": "application/json",
    "Cache-Control": "public, max-age=60",
    Vary: "X-Shaidago-Locale",
    "Content-Language": locale
  });
  response.end(JSON.stringify(body));
}

function encodeCursor(offset, filters) {
  return Buffer.from(JSON.stringify({ offset, filters })).toString("base64url");
}

function decodeCursor(value) {
  try {
    const parsed = JSON.parse(Buffer.from(value, "base64url").toString("utf8"));

    return Number.isInteger(parsed.offset) && parsed.offset >= 0 ? parsed : undefined;
  } catch {
    return undefined;
  }
}

createServer((request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${port}`);
  const path = url.pathname;

  if (path === "/__mode" && request.method === "POST") {
    let body = "";
    request.on("data", (chunk) => (body += chunk));
    request.on("end", () => {
      const next = JSON.parse(body || "{}");
      mode = next.mode ?? "ok";
      projects = makeProjects(next.count ?? (mode === "empty" ? 0 : 30));
      response.writeHead(204).end();
    });
    return;
  }
  if (path === "/__stats") {
    if (request.method === "POST") {
      for (const key of Object.keys(stats)) delete stats[key];
      response.writeHead(204).end();
      return;
    }
    response.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify(stats));
    return;
  }
  if (path === "/health/live") {
    response.writeHead(200, { "Content-Type": "application/json" }).end('{"status":"live"}');
    return;
  }

  if (request.headers.authorization !== `Bearer web.${credential}`) {
    problem(response, 401, "unauthenticated");
    return;
  }

  // Counted per exact URL, so a test can probe its own unique query without interference.
  stats[path + url.search] = (stats[path + url.search] ?? 0) + 1;
  const locale = String(request.headers["x-shaidago-locale"] ?? "en");

  if (mode === "down") {
    problem(response, 503, "dependency_unavailable");
    return;
  }
  if (mode === "slow") {
    setTimeout(() => problem(response, 503, "dependency_unavailable"), 8000);
    return;
  }

  if (path === "/v1/localities") {
    json(response, { items: LOCALITIES }, locale);
    return;
  }

  if (path === "/v1/projects") {
    const query = url.searchParams;
    const limit = Math.min(Number(query.get("limit") ?? 20), 50);
    const filters = {};

    for (const name of ["q", "locality", "category", "status", "verification"]) {
      if (query.get(name) !== null) filters[name] = query.get(name);
    }

    // Stateless test switches, so browser projects running in parallel cannot interfere.
    if (filters.q === "__unavailable") {
      problem(response, 503, "dependency_unavailable");
      return;
    }
    if (filters.q === "__slow") {
      setTimeout(() => problem(response, 503, "dependency_unavailable"), 8000);
      return;
    }

    const key = JSON.stringify(filters);
    let offset = 0;

    if (query.get("cursor") !== null) {
      const cursor = decodeCursor(query.get("cursor"));

      if (cursor === undefined || JSON.stringify(cursor.filters) !== key) {
        problem(response, 400, "invalid_cursor");
        return;
      }
      offset = cursor.offset;
    }

    const matching = projects.filter(
      (project) =>
        (filters.locality === undefined || project.locality_slug === filters.locality) &&
        (filters.category === undefined || project.category === filters.category) &&
        (filters.status === undefined || project.public_status === filters.status) &&
        (filters.verification === undefined || project.verification === filters.verification) &&
        (filters.q === undefined ||
          `${project.title} ${project.summary}`.toLowerCase().includes(filters.q.toLowerCase()))
    );
    const page = matching.slice(offset, offset + limit);
    const next = offset + limit < matching.length ? encodeCursor(offset + limit, filters) : null;
    const fallback = locale !== "en";

    json(
      response,
      {
        items: page.map((project) => ({
          category: project.category,
          last_checked_on: project.last_checked_on,
          locality_slug: project.locality_slug,
          public_status: project.public_status,
          slug: project.slug,
          text: {
            is_fallback: fallback,
            served_locale: "en",
            summary: project.summary,
            title: project.title,
            translation_status: "reviewed"
          },
          updated_at: project.updated_at
        })),
        next_cursor: next
      },
      locale
    );
    return;
  }

  problem(response, 404, "not_found");
}).listen(port, "127.0.0.1", () => {
  process.stdout.write(`mock api on ${port}\n`);
});
