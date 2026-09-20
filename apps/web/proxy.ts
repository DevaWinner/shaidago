import createMiddleware from "next-intl/middleware";

import { routing } from "./src/i18n/routing";

/**
 * Locale negotiation for public pages. The matcher leaves the BFF (`/api`), framework assets, and
 * any path with a file extension (such as `/robots.txt`) untouched, so browser mutations keep their
 * unprefixed same-origin URLs. Redirects are always relative to this origin.
 */
export default createMiddleware(routing);

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"]
};
