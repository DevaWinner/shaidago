import { handlePublicJson } from "@/lib/bff/public-handler";
import { statusLookupInput } from "@/lib/bff/public-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-JSON: report_status_lookup. The code travels only in the body and is never logged.
export function POST(request: Request): Promise<Response> {
  return handlePublicJson(request, {
    schema: statusLookupInput,
    maxBodyBytes: 2 * 1024,
    idempotent: false,
    call: (api, input, options) => api.lookupReportStatus(input, options)
  });
}
