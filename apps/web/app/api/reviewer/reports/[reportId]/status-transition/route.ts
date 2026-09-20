import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { dropUndefined, transitionInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_decisions_transition. The API alone decides whether it is allowed.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: transitionInput,
    maxBodyBytes: 4 * 1024,
    call: (api, ids, input, options) =>
      api.transitionReport(ids.reportId, dropUndefined(input), options)
  });
}
