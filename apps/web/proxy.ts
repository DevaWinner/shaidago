import type { NextRequest, NextResponse } from "next/server";
import createMiddleware from "next-intl/middleware";

import { routing } from "./src/i18n/routing";

/**
 * Locale negotiation for public pages. The matcher leaves the BFF (`/api`), framework assets, and
 * any path with a file extension (such as `/robots.txt`) untouched, so browser mutations keep their
 * unprefixed same-origin URLs. Redirects are always relative to this origin.
 */
const intl = createMiddleware(routing);

const HSTS = "max-age=31536000; includeSubDomains";

/**
 * Strict-Transport-Security is sent only in the deployed stages (and only for requests that arrived
 * over HTTPS), never on local HTTP where it would pin a developer's `localhost`. Preloading is a
 * separate, deliberate decision and is not requested here.
 */
export default function proxy(request: NextRequest): NextResponse {
  const response = intl(request) as NextResponse;
  const deployed = process.env["APP_ENV"] === "staging" || process.env["APP_ENV"] === "production";
  const secure =
    request.headers.get("x-forwarded-proto") === "https" || request.nextUrl.protocol === "https:";

  if (deployed && secure) {
    response.headers.set("Strict-Transport-Security", HSTS);
  }

  return response;
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"]
};
