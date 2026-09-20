import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { discoveryAnswerInput, dropUndefined } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_discovery_answer_follow_up. Answers are encrypted by the API.
export function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: discoveryAnswerInput,
    maxBodyBytes: 4 * 1024,
    call: (api, ids, input, options) =>
      api.answerDiscoveryFollowUp(ids.runId, dropUndefined(input), options)
  });
}
