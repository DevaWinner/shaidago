import { revalidatePublicCatalogue } from "@/lib/bff/public-cache";
import { handleReviewerJson } from "@/lib/bff/reviewer-handler";
import { publishInput } from "@/lib/bff/reviewer-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REVIEWER-JSON: reviewer_publication_publish. Confirms one exact preview digest.
export function POST(
  request: Request,
  { params }: { params: Promise<{ reportId: string; updateId: string }> }
): Promise<Response> {
  return handleReviewerJson(request, params, {
    schema: publishInput,
    maxBodyBytes: 2 * 1024,
    // A published update changes public pages, so cached public reads are dropped immediately.
    afterSuccess: revalidatePublicCatalogue,
    call: (api, ids, input, options) =>
      api.publishUpdate(ids.reportId, ids.updateId, input, options)
  });
}
