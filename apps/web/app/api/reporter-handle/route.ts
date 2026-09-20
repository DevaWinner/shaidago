import { handlePublicEmpty } from "@/lib/bff/public-handler";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-IDEMPOTENT-EMPTY: reporter_handles_create. One-time credentials; never persisted.
export function POST(request: Request): Promise<Response> {
  return handlePublicEmpty(request, {
    idempotent: true,
    call: (api, options) => api.createReporterHandle(options)
  });
}
