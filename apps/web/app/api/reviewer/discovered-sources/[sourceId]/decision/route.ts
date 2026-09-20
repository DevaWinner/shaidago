import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { decisionInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_discovery_decide_source. Attach creates a pending source, never a fact.
export function POST(
  request: Request,
  { params }: { params: Promise<{ sourceId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: decisionInput,
    maxBodyBytes: 4 * 1024,
    call: (api, ids, input, options) => api.decideDiscoveredSource(ids.sourceId, input, options)
  });
}
