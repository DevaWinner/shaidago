import { handleReviewerGet } from "@/lib/bff/reviewer-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-GET: reviewer_publication_preview.
export function GET(
  request: Request,
  { params }: { params: Promise<{ reportId: string; updateId: string }> }
): Promise<Response> {
  return handleReviewerGet(request, params, (api, ids, options) =>
    api.getPublicationPreview(ids.reportId, ids.updateId, options)
  );
}
