import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { runCreateInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_discovery_create. Requires the approved plan digest.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: runCreateInput,
    maxBodyBytes: 8 * 1024,
    call: (api, ids, input, options) => api.createDiscoveryRun(ids.reportId, input, options)
  });
}
