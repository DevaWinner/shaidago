import { loadServerEnvironment } from "@/lib/config/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * Readiness: the service's own configuration is valid. It deliberately does not call the private
 * API, so an API outage degrades only the pages that need it, never project browsing from cache or
 * the offline page. It reports no value from the environment, only whether it is usable.
 */
export function GET(): Response {
  try {
    loadServerEnvironment();

    return Response.json({ status: "ready" }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json(
      { status: "not_ready" },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}
