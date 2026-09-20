export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/** Liveness only: the process answers. It touches no dependency, so a private-API outage never restarts the web service. */
export function GET(): Response {
  return Response.json({ status: "live" }, { headers: { "Cache-Control": "no-store" } });
}
