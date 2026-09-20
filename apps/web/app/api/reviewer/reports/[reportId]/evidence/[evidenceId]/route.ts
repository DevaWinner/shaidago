import { handleEvidenceDownload } from "@/lib/bff/reviewer-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-EVIDENCE-STREAM: reviewer_evidence_download. Streams one sanitised attachment; no signed URL.
export function GET(
  request: Request,
  { params }: { params: Promise<{ reportId: string; evidenceId: string }> }
): Promise<Response> {
  return handleEvidenceDownload(request, params);
}
