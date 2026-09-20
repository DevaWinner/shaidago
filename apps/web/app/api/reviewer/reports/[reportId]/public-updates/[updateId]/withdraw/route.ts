import { handleReviewerEmpty } from "@/lib/bff/reviewer-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-EMPTY: reviewer_publication_withdraw. The API takes no body for this command.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string; updateId: string }> }
): Promise<Response> {
  return handleReviewerEmpty(request, params, (api, ids, options) =>
    api.withdrawUpdate(ids.reportId, ids.updateId, options)
  );
}
