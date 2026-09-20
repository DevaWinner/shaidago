import { NextRequest } from "next/server";

import { serverApi } from "@/lib/api/server";
import { noStoreHeaders, problemResponse } from "@/lib/bff/problem";
import { resultResponse } from "@/lib/bff/public-handler";
import { runIdSchema, sinceVersionSchema } from "@/lib/bff/public-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-GET: discovery_get_public_run. Opaque run ID and optional `since_version` only.
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ runId: string }> }
): Promise<Response> {
  const requestId = crypto.randomUUID();

  try {
    const { runId } = await context.params;
    const query = request.nextUrl.searchParams;
    const unknownParameter = [...query.keys()].some((name) => name !== "since_version");
    const run = runIdSchema.safeParse(runId);
    const since = query.has("since_version")
      ? sinceVersionSchema.safeParse(query.get("since_version"))
      : undefined;

    if (
      unknownParameter ||
      query.getAll("since_version").length > 1 ||
      !run.success ||
      since?.success === false
    ) {
      return problemResponse({
        status: 422,
        code: "validation_failed",
        requestId,
        fieldErrors: [{ field: "query", code: "invalid" }]
      });
    }

    const result = await serverApi().getPublicDiscoveryRun(run.data, since?.data, {
      context: { requestId, locale: request.headers.get("X-Shaidago-Locale") },
      signal: request.signal
    });

    if (result.kind === "not_modified") {
      return new Response(null, { status: 304, headers: noStoreHeaders(requestId) });
    }

    return resultResponse(result);
  } catch {
    return problemResponse({ status: 500, code: "internal_error", requestId });
  }
}
