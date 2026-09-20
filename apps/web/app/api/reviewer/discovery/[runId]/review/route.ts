import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { reviewInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_discovery_review.
export function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: reviewInput,
    maxBodyBytes: 2 * 1024,
    call: (api, ids, input, options) => api.reviewDiscoveryRun(ids.runId, input, options)
  });
}
