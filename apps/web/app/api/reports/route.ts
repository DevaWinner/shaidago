import { handleReportSubmission } from "@/lib/bff/public-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-REPORT-MULTIPART: reports_submit. Streams ≤ 30 MiB + 64 KiB; Idempotency-Key required.
export function POST(request: Request): Promise<Response> {
  return handleReportSubmission(request);
}
