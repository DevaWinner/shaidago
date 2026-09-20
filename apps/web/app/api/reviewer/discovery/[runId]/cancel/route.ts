import { handleReviewerEmpty } from "@/lib/bff/reviewer-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-EMPTY: reviewer_discovery_cancel.
export function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> }
): Promise<Response> {
  return handleReviewerEmpty(request, params, (api, ids, options) =>
    api.cancelDiscoveryRun(ids.runId, options)
  );
}
