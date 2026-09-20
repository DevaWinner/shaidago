import { toSafeRequestReference } from "@/lib/support/request-reference";

export const API_LOCALES = ["en", "ha", "ig", "yo"] as const;
export type ApiLocale = (typeof API_LOCALES)[number];

const CLIENT_HMAC_PATTERN = /^[0-9a-f]{64}$/;
// Strong or weak entity tag: a quoted printable-ASCII value, bounded so it cannot smuggle a header.
const ETAG_PATTERN = /^(?:W\/)?"[\x21\x23-\x7e]{1,200}"$/;

export function toApiLocale(value: unknown): ApiLocale | undefined {
  return API_LOCALES.find((locale) => locale === value);
}

export function toClientHmac(value: unknown): string | undefined {
  return typeof value === "string" && CLIENT_HMAC_PATTERN.test(value) ? value : undefined;
}

export function toEntityTag(value: unknown): string | undefined {
  return typeof value === "string" && ETAG_PATTERN.test(value) ? value : undefined;
}

export type ForwardedContext = {
  readonly requestId?: unknown;
  readonly locale?: unknown;
  readonly clientHmac?: unknown;
};

/**
 * Builds only the context headers the API accepts after service authentication (ADR-0002).
 * Every value is re-validated here so an untrusted caller cannot inject an arbitrary header.
 * The request ID is always present: a missing or malformed one is replaced, never forwarded.
 */
export function buildForwardedHeaders(
  context: ForwardedContext,
  generateRequestId: () => string
): { readonly headers: Record<string, string>; readonly requestId: string } {
  const requestId = toSafeRequestReference(context.requestId) ?? generateRequestId();
  const headers: Record<string, string> = { "X-Request-Id": requestId };
  const locale = toApiLocale(context.locale);
  const clientHmac = toClientHmac(context.clientHmac);

  if (locale !== undefined) {
    headers["X-Shaidago-Locale"] = locale;
  }

  if (clientHmac !== undefined) {
    headers["X-Shaidago-Client-Hmac"] = clientHmac;
  }

  return { headers, requestId };
}
