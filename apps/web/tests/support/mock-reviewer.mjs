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

  return false;
}
