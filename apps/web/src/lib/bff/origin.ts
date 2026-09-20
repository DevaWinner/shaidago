export type OriginPolicy = {
  /** Exact origins (scheme, host, port) allowed to mutate. Empty means every mutation is refused. */
  readonly allowedOrigins: readonly string[];
};

export type OriginPolicyInput = {
  readonly appEnvironment: "development" | "test" | "staging" | "production";
  /** The configured public origin, e.g. `https://shaidago.example`. */
  readonly publicOrigin: string | undefined;
  /** The URL the runtime received; only its own origin is used, and only outside deployed stages. */
  readonly requestUrl: string;
  /**
   * The `Host` the browser used. The framework may report a different host name than the address
   * a developer typed (`localhost` versus `127.0.0.1`), so development and test also accept it.
   * It is never consulted in staging or production, where the configured public origin decides.
   */
  readonly requestHost?: string | null | undefined;
};

function normaliseOrigin(value: string): string | undefined {
  if (!URL.canParse(value)) {
    return undefined;
  }

  const url = new URL(value);

  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return undefined;
  }

  return url.origin;
}

/**
 * Forwarded headers (`X-Forwarded-Host`, `X-Forwarded-Proto`, `Forwarded`) are never consulted:
 * a client can set them. Deployed stages trust only the configured public origin. Development and
 * test also trust the origin the local server itself received, so `http://localhost` works without
 * configuration; a deployed stage with no configured origin refuses every mutation.
 */
export function resolveOriginPolicy(input: OriginPolicyInput): OriginPolicy {
  const configured =
    input.publicOrigin === undefined ? undefined : normaliseOrigin(input.publicOrigin);
  const isLocalStage = input.appEnvironment === "development" || input.appEnvironment === "test";
  const local = isLocalStage ? normaliseOrigin(input.requestUrl) : undefined;
  const host =
    isLocalStage && typeof input.requestHost === "string" && input.requestHost !== ""
      ? normaliseOrigin(`http://${input.requestHost}`)
      : undefined;

  return {
    allowedOrigins: [
      ...new Set([configured, local, host].filter((o): o is string => o !== undefined))
    ]
  };
}

export type OriginCheck = { readonly ok: true } | { readonly ok: false };

/**
 * Requires exactly one `Origin` header equal to a trusted origin. A missing, `null`, repeated
 * (comma-joined by the Headers API), or malformed value fails. `Sec-Fetch-Site` is a second
 * signal, not a substitute: a browser reporting `cross-site` is refused even with a matching Origin.
 */
export function checkOrigin(headers: Headers, policy: OriginPolicy): OriginCheck {
  const origin = headers.get("Origin");

  if (origin === null || origin.includes(",")) {
    return { ok: false };
  }

  const fetchSite = headers.get("Sec-Fetch-Site");

  if (fetchSite === "cross-site") {
    return { ok: false };
  }

  const normalised = normaliseOrigin(origin);

  if (normalised === undefined || normalised !== origin) {
    return { ok: false };
  }

  return policy.allowedOrigins.includes(normalised) ? { ok: true } : { ok: false };
}
