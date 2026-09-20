import { handlePublicJson } from "@/lib/bff/public-handler";
import { questionInput } from "@/lib/bff/public-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-JSON: projects_ask_question. Body ≤ 4 KiB; no idempotency key; no-store.
export function POST(request: Request): Promise<Response> {
  return handlePublicJson(request, {
    schema: questionInput,
    maxBodyBytes: 4 * 1024,
    idempotent: false,
    call: (api, input, options) =>
      api.askQuestion(input.slug, { question: input.question }, options)
  });
}
