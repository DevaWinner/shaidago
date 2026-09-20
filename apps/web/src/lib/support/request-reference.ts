const REQUEST_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

/**
 * A displayed support reference is operational metadata, never error text. Keeping the allowlist
 * here prevents a boundary from accidentally rendering a stack trace, provider response, or ID
 * with an unexpected format.
 */
export function toSafeRequestReference(value: unknown): string | undefined {
  if (typeof value !== "string" || !REQUEST_ID_PATTERN.test(value)) {
    return undefined;
  }

  return value.toLowerCase();
}
