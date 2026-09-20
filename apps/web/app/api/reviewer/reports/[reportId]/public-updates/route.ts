import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { draftInput, dropUndefined } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_publication_create_draft. Creates a private preview only.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: draftInput,
    maxBodyBytes: 16 * 1024,
    call: (api, ids, input, options) =>
      api.createPublicationDraft(ids.reportId, dropUndefined(input), options)
  });
}
