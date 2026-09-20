import { handleReviewerGet } from "@/lib/bff/reviewer-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-GET: reviewer_discovery_get. Report-scoped run; never cached.
export function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string }> }
): Promise<Response> {
  return handleReviewerGet(request, params, (api, ids, options) =>
    api.getReviewerDiscoveryRun(ids.runId, options)
  );
}
