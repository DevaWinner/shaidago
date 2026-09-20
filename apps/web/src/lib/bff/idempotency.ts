// The API accepts only a lower-case canonical UUID (no braces, no upper case, hyphens required).
const IDEMPOTENCY_KEY_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export function toIdempotencyKey(value: unknown): string | undefined {
  return typeof value === "string" && IDEMPOTENCY_KEY_PATTERN.test(value) ? value : undefined;
}

/**
 * A key identifies one user intent. Generate it once when the intent begins and reuse it for every
 * retry of that same intent; a handler must never call this while retrying.
 */
export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
