import { handlePublicJson } from "@/lib/bff/public-handler";
import { credentialsInput } from "@/lib/bff/public-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-JSON: reporter_handles_list_reports. Credentials only in the body.
export function POST(request: Request): Promise<Response> {
  return handlePublicJson(request, {
    schema: credentialsInput,
    maxBodyBytes: 2 * 1024,
    idempotent: false,
    call: (api, input, options) => api.listHandleReports(input, options)
  });
}
