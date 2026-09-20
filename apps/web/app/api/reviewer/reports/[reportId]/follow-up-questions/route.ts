import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { reviewerQuestionInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_decisions_ask_follow_up. Body ≤ 2 KiB.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: reviewerQuestionInput,
    maxBodyBytes: 2 * 1024,
    call: (api, ids, input, options) => api.askReviewerFollowUp(ids.reportId, input, options)
  });
}
