import { handlePublicJson } from "@/lib/bff/public-handler";
import { credentialsInput } from "@/lib/bff/public-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-JSON: reporter_handles_delete. Unlinks reports; reports stay anonymous.
export function POST(request: Request): Promise<Response> {
  return handlePublicJson(request, {
    schema: credentialsInput,
    maxBodyBytes: 2 * 1024,
    idempotent: false,
    call: (api, input, options) => api.deleteReporterHandle(input, options)
  });
}
