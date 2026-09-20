import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { planInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_discovery_plan. Returns the exact outbound query for approval.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: planInput,
    maxBodyBytes: 4 * 1024,
    call: (api, ids, input, options) => api.planDiscovery(ids.reportId, input, options)
  });
}
