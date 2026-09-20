import { z } from "zod";

import type { SafeProblem } from "@/lib/problems/problem-messages";

const REQUEST_ID = /^[0-9a-f-]{36}$/i;
const CODE = /^[a-z][a-z0-9_]{1,63}$/;

// Only these fields are read. `title` and `detail` are deliberately absent so they cannot be used.
const bodySchema = z.object({
  code: z.string().regex(CODE),
  status: z.number().int().optional(),
  request_id: z.string().regex(REQUEST_ID).nullish(),
  errors: z
    .array(z.object({ field: z.string().max(200), code: z.string().regex(CODE) }))
    .max(50)
    .nullish()
});

function retryAfter(headers: Headers): number | undefined {
  const value = headers.get("Retry-After");

  return value !== null && /^\d{1,4}$/.test(value) ? Number(value) : undefined;
}

/**
 * Reads a failed BFF response into a `SafeProblem`. An unreadable body, a non-problem content type,
 * or a malformed shape becomes `internal_error` rather than displaying anything from it.
 */
export async function readBrowserProblem(response: Response): Promise<SafeProblem> {
  const isProblem = (response.headers.get("Content-Type") ?? "").startsWith(
    "application/problem+json"
  );
  let parsed: z.infer<typeof bodySchema> | undefined;

  if (isProblem) {
    try {
      const result = bodySchema.safeParse(await response.json());
      parsed = result.success ? result.data : undefined;
    } catch {
      parsed = undefined;
    }
  }

  return {
    code: parsed?.code ?? "internal_error",
    status: response.status,
    requestId: parsed?.request_id ?? response.headers.get("X-Request-Id") ?? undefined,
    retryAfterSeconds: retryAfter(response.headers),
    fieldErrors: (parsed?.errors ?? []).map(({ field, code }) => ({ field, code }))
  };
}

/** A failure with no response at all: offline, blocked, or the connection dropped. */
export function networkProblem(): SafeProblem {
  return {
    code: "network_unavailable",
    status: undefined,
    requestId: undefined,
    retryAfterSeconds: undefined,
    fieldErrors: []
  };
}
