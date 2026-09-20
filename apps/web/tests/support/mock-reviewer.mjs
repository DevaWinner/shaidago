/**
 * Fictional reviewer endpoints for the browser test servers. Everything returned is synthetic.
 * It enforces the same header contract as the real API (`X-Shaidago-Session`, and
 * `X-Shaidago-Csrf` on mutations), so a test proves the BFF forwarded the HttpOnly cookies, and it
 * records only counts and request shapes, never a credential value.
 */

export const SESSION_TOKEN = "fictional-session-token-0123456789abcdef";
export const CSRF_TOKEN = "fictional-csrf-token-0123456789abcdef0";
export const IDENTIFIER = "reviewer-demo";
export const PASSWORD = "fictional-password-not-a-secret";

const log = [];

const STATUSES = [
  "received",
  "needs_information",
  "under_review",
  "verified_for_public_update",
  "referred",
  "closed"
];
const RISKS = ["standard", "elevated", "high"];
const CATEGORIES = [
  "no_visible_work",
  "incomplete_work",
  "unsafe_construction",
  "suspected_incorrect_status",
  "access_barrier",
  "other_concern"
];
const PROJECTS = ["synthetic-example-clinic", "synthetic-example-school", "synthetic-example-road"];

export const REPORT_IDS = [];

const queue = Array.from({ length: 45 }, (_, index) => {
  const report_id = `0198f1a2-7b3c-4d4e-8f5a-${String(index + 1).padStart(12, "0")}`;

  REPORT_IDS.push(report_id);

  return {
    report_id,
    project_slug: PROJECTS[index % PROJECTS.length],
    concern_category: CATEGORIES[index % CATEGORIES.length],
    risk_level: RISKS[index % RISKS.length],
    status: STATUSES[index % STATUSES.length],
    version: 1 + (index % 3),
    created_at: `2026-09-${String(1 + (index % 28)).padStart(2, "0")}T09:00:00Z`,
    status_updated_at: `2026-09-${String(2 + (index % 27)).padStart(2, "0")}T10:00:00Z`,
    has_contact: index % 4 === 0,
    evidence_count: index % 3,
    open_follow_ups: index % 5 === 0 ? 1 : 0
  };
});

function cursorFor(offset, key) {
  return Buffer.from(JSON.stringify({ offset, key })).toString("base64url");
}

function offsetFrom(value, key) {
  try {
    const parsed = JSON.parse(Buffer.from(value, "base64url").toString("utf8"));

    return parsed.key === key && Number.isInteger(parsed.offset) ? parsed.offset : undefined;
  } catch {
    return undefined;
  }
}

export function reviewerLog() {
  return log;
}

export function resetReviewer() {
  log.length = 0;
}

function json(response, status, body, headers = {}) {
  response.writeHead(status, {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
    ...headers
  });
  response.end(JSON.stringify(body));
}

function authorised(request) {
  return request.headers["x-shaidago-session"] === SESSION_TOKEN;
}

function hasCsrf(request) {
  return request.headers["x-shaidago-csrf"] === CSRF_TOKEN;
}

/** Returns true when the request was a reviewer request and has been answered. */
export function handleReviewer({ request, response, url, problem, readBody }) {
  const path = url.pathname;
  const method = request.method;

  if (path === "/v1/auth/sessions" && method === "POST") {
    readBody(request, (body) => {
      log.push({ op: "sign_in" });

      if (body?.identifier === "rate-limited") {
        problem(response, 429, "rate_limited", { "Retry-After": "2" });
      } else if (body?.identifier === IDENTIFIER && body?.password === PASSWORD) {
        json(response, 201, {
          session_token: SESSION_TOKEN,
          csrf_token: CSRF_TOKEN,
          expires_at: "2099-01-01T00:00:00Z",
          idle_timeout_seconds: 1800,
          cookie: {
            name: "sg_session",
            secure: false,
            http_only: true,
            same_site: "lax",
            path: "/",
            max_age_seconds: 3600
          },
          reviewer: { role: "reviewer" }
        });
      } else {
        problem(response, 401, "invalid_credentials");
      }
    });
    return true;
  }

  if (path === "/v1/auth/sessions/current" && method === "DELETE") {
    log.push({ op: "sign_out", csrf: hasCsrf(request) });
    response.writeHead(204, { "Cache-Control": "no-store" }).end();
    return true;
  }

  if (!path.startsWith("/v1/reviewer/")) {
    return false;
  }

  if (!authorised(request)) {
    problem(response, 401, "unauthenticated");
    return true;
  }

  if (path === "/v1/reviewer/reports" && method === "GET") {
    const query = url.searchParams;
    const project = query.get("project");

    if (project === "zz-unavailable") {
      problem(response, 503, "dependency_unavailable");
      return true;
    }
    if (project === "zz-forbidden") {
      problem(response, 403, "forbidden");
      return true;
    }
    if (project === "zz-limited") {
      problem(response, 429, "rate_limited", { "Retry-After": "5" });
      return true;
    }

    const statuses = query.getAll("status");
    const key = JSON.stringify([
      statuses,
      query.get("risk_level"),
      query.get("concern_category"),
      project
    ]);
    const limit = Math.min(Number(query.get("limit") ?? 20), 50);
    let offset = 0;

    if (query.get("cursor") !== null) {
      const parsed = offsetFrom(query.get("cursor"), key);

      if (parsed === undefined) {
        problem(response, 400, "invalid_cursor");
        return true;
      }
      offset = parsed;
    }

    log.push({ op: "queue", filters: key });
    const matching = queue.filter(
      (item) =>
        (statuses.length === 0 || statuses.includes(item.status)) &&
        (query.get("risk_level") === null || item.risk_level === query.get("risk_level")) &&
        (query.get("concern_category") === null ||
          item.concern_category === query.get("concern_category")) &&
        (project === null || item.project_slug === project)
    );

    json(response, 200, {
      items: matching.slice(offset, offset + limit),
      next_cursor: offset + limit < matching.length ? cursorFor(offset + limit, key) : null
    });
    return true;
  }

  return false;
}
