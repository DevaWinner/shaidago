import { handlePublicJson } from "@/lib/bff/public-handler";
import { discoveryStartInput } from "@/lib/bff/public-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-JSON: discovery_start_public_run. Body ≤ 2 KiB; opaque project slug only.
export function POST(request: Request): Promise<Response> {
  return handlePublicJson(request, {
    schema: discoveryStartInput,
    maxBodyBytes: 2 * 1024,
    idempotent: false,
    call: (api, input, options) => api.startPublicDiscovery(input.slug, options)
  });
}
