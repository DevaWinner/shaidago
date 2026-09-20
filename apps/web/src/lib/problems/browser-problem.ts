import type { SafeProblem } from "@/lib/problems/problem-messages";

const REQUEST_ID = /^[0-9a-f-]{36}$/i;
const CODE = /^[a-z][a-z0-9_]{1,63}$/;

type ParsedProblem = Readonly<{
  code: string;
  requestId: string | undefined;
  errors: readonly { field: string; code: string }[];
}>;

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Only `code`, `request_id`, and field paths with rule codes are read; `title` and `detail` are
 * deliberately absent so they cannot be used. Hand-checked rather than a schema library so this
 * browser module does not add a validator to every page's first-load JavaScript. Any mismatch
 * rejects the whole body.
 */
function parseProblem(value: unknown): ParsedProblem | undefined {
  if (!isRecord(value) || typeof value["code"] !== "string" || !CODE.test(value["code"])) {
    return undefined;
  }

  const requestId = value["request_id"];

  if (requestId !== undefined && requestId !== null) {
    if (typeof requestId !== "string" || !REQUEST_ID.test(requestId)) {
      return undefined;
    }
  }

  const status = value["status"];

  if (status !== undefined && !(typeof status === "number" && Number.isInteger(status))) {
    return undefined;
  }

  const raw = value["errors"];
  const errors: { field: string; code: string }[] = [];

  if (raw !== undefined && raw !== null) {
    if (!Array.isArray(raw) || raw.length > 50) {
      return undefined;
    }
    for (const entry of raw as unknown[]) {
      if (
        !isRecord(entry) ||
        typeof entry["field"] !== "string" ||
        entry["field"].length > 200 ||
        typeof entry["code"] !== "string" ||
        !CODE.test(entry["code"])
      ) {
        return undefined;
      }
      errors.push({ field: entry["field"], code: entry["code"] });
    }
  }

  return {
    code: value["code"],
    requestId: typeof requestId === "string" ? requestId : undefined,
    errors
  };
}

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
  let parsed: ParsedProblem | undefined;

  if (isProblem) {
    try {
      parsed = parseProblem(await response.json());
    } catch {
      parsed = undefined;
    }
  }

  return {
    code: parsed?.code ?? "internal_error",
    status: response.status,
    requestId: parsed?.requestId ?? response.headers.get("X-Request-Id") ?? undefined,
    retryAfterSeconds: retryAfter(response.headers),
    fieldErrors: parsed?.errors ?? []
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
