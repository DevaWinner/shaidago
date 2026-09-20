import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { noteInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_notes_create. Body ≤ 8 KiB.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: noteInput,
    maxBodyBytes: 8 * 1024,
    call: (api, ids, input, options) => api.createNote(ids.reportId, input, options)
  });
}
