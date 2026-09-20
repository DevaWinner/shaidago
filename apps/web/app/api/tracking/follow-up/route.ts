import { handlePublicJson } from "@/lib/bff/public-handler";
import { followUpInput, toAnswerRequest } from "@/lib/bff/public-schemas";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// BFF-PUBLIC-IDEMPOTENT: report_status_answer_follow_up. Body ≤ 8 KiB; one credential form.
export function POST(request: Request): Promise<Response> {
  return handlePublicJson(request, {
    schema: followUpInput,
    maxBodyBytes: 8 * 1024,
    idempotent: true,
    call: (api, input, options) => api.answerFollowUp(toAnswerRequest(input), options)
  });
}
