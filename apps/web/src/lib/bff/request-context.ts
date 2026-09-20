import "server-only";

import { createHmac } from "node:crypto";
import { isIP } from "node:net";

import type { ForwardedContext } from "@/lib/api/forwarded-context";
import { loadServerEnvironment } from "@/lib/config/server";

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Picks the client address the trusted edge appended. `X-Forwarded-For` is client-writable at its
 * left end, so only the entry `hops` places from the right (added by our own proxies) is used.
 * With zero hops there is no trustworthy source and no address is returned.
 */
export function trustedClientAddress(header: string | null, hops: number): string | undefined {
  if (header === null || hops < 1) {
    return undefined;
  }

  const parts = header.split(",").map((part) => part.trim());
  const candidate = parts[parts.length - hops];

  return candidate !== undefined && isIP(candidate) !== 0 ? candidate : undefined;
}

/**
 * A pseudonymous rate-limit key: HMAC-SHA256 of the address under a server-only key, rotated by
 * UTC day so it cannot be linked across days. The address itself is never forwarded or stored.
 */
export function deriveClientHmac(
  address: string | undefined,
  key: Buffer | undefined,
  now: number
): string | undefined {
  if (address === undefined || key === undefined) {
    return undefined;
  }

  return createHmac("sha256", key)
    .update(`${Math.floor(now / DAY_MS)}:${address}`)
    .digest("hex");
}

/** The validated context every backend call carries: request ID, locale, and client HMAC. */
export function forwardedContextForHeaders(
  headers: Pick<Headers, "get">,
  requestId: string
): ForwardedContext {
  const environment = loadServerEnvironment();
  const address = trustedClientAddress(
    headers.get("X-Forwarded-For"),
    environment.trustedProxyHops
  );

  return {
    requestId,
    locale: headers.get("X-Shaidago-Locale"),
    clientHmac: deriveClientHmac(address, environment.clientHmacKey, Date.now())
  };
}

export function forwardedContextFor(request: Request, requestId: string): ForwardedContext {
  return forwardedContextForHeaders(request.headers, requestId);
}
