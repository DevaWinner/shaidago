export type ContentTypeRule = "json" | "multipart";

export type BodyLimitFailure = "payload_too_large" | "unsupported_media_type" | "invalid_json";

export class BodyRejectedError extends Error {
  public constructor(public readonly reason: BodyLimitFailure) {
    super(reason);
    this.name = "BodyRejectedError";
  }
}

/** Returns the lower-cased media type without parameters, or undefined when absent or malformed. */
function mediaType(headers: Headers): string | undefined {
  const value = headers.get("Content-Type");

  if (value === null) {
    return undefined;
  }

  const [type] = value.split(";");

  return type?.trim().toLowerCase() || undefined;
}

export function hasAllowedContentType(headers: Headers, rule: ContentTypeRule): boolean {
  const type = mediaType(headers);

  if (rule === "json") {
    return type === "application/json";
  }

  return (
    type === "multipart/form-data" &&
    /;\s*boundary=[^;\s]+/i.test(headers.get("Content-Type") ?? "")
  );
}

/**
 * Rejects on headers alone, before any body byte is read. A declared length above the cap is
 * refused; a missing or non-numeric length is allowed because chunked bodies are still counted
 * as they stream (see `limitBodyStream`).
 */
export function preflightBody(headers: Headers, rule: ContentTypeRule, maxBytes: number): void {
  if (!hasAllowedContentType(headers, rule)) {
    throw new BodyRejectedError("unsupported_media_type");
  }

  const declared = headers.get("Content-Length");

  if (declared !== null && (!/^\d{1,15}$/.test(declared) || Number(declared) > maxBytes)) {
    throw new BodyRejectedError("payload_too_large");
  }
}

/** Counts bytes as they pass and errors the stream the moment the cap is exceeded. */
export function limitBodyStream(
  body: ReadableStream<Uint8Array>,
  maxBytes: number
): ReadableStream<Uint8Array> {
  let seen = 0;

  return body.pipeThrough(
    new TransformStream<Uint8Array, Uint8Array>({
      transform(chunk, controller) {
        seen += chunk.byteLength;

        if (seen > maxBytes) {
          controller.error(new BodyRejectedError("payload_too_large"));
          return;
        }

        controller.enqueue(chunk);
      }
    })
  );
}

async function readAll(stream: ReadableStream<Uint8Array>): Promise<Uint8Array> {
  const chunks: Uint8Array[] = [];
  let total = 0;

  const reader = stream.getReader();

  for (let next = await reader.read(); !next.done; next = await reader.read()) {
    chunks.push(next.value);
    total += next.value.byteLength;
  }

  const bytes = new Uint8Array(total);
  let offset = 0;

  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }

  return bytes;
}

/**
 * Preflights, streams the body under the cap, and parses JSON. It returns `unknown`; the caller's
 * schema is the only thing allowed to narrow it. An empty body is `undefined`.
 */
export async function readBoundedJson(request: Request, maxBytes: number): Promise<unknown> {
  preflightBody(request.headers, "json", maxBytes);

  if (request.body === null) {
    return undefined;
  }

  const bytes = await readAll(limitBodyStream(request.body, maxBytes));

  if (bytes.byteLength === 0) {
    return undefined;
  }

  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)) as unknown;
  } catch {
    throw new BodyRejectedError("invalid_json");
  }
}
