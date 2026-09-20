import { handleReviewerEmpty } from "@/lib/bff/reviewer-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-EMPTY: reviewer_decisions_withdraw_follow_up.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string; questionId: string }> }
): Promise<Response> {
  return handleReviewerEmpty(request, params, (api, ids, options) =>
    api.withdrawReviewerFollowUp(ids.reportId, ids.questionId, options)
  );
}
