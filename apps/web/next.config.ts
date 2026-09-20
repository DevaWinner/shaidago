import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const development = process.env["NODE_ENV"] !== "production";

/**
 * Browser security headers for every response. The policy allows only this origin: no third-party
 * script, style, font, image, frame, or connection is permitted, so none can be added without
 * changing this file. `'unsafe-inline'` remains for scripts and styles because the framework emits
 * inline bootstrap data and the low-data head script; moving to per-request nonces would make every
 * page dynamic, so it is a recorded trade-off, not an oversight. HSTS is added at runtime by
 * `proxy.ts` for staging and production only, because it must never be sent over local HTTP.
 */
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${development ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  `connect-src 'self'${development ? " ws: wss:" : ""}`,
  "worker-src 'self'",
  "manifest-src 'self'",
  "frame-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'"
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "same-origin" },
  {
    key: "Permissions-Policy",
    value:
      "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), bluetooth=(), interest-cohort=()"
  },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" }
];

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  typedRoutes: true,
  async headers() {
    // The public catalogue pages carry no private data, so they may be stored by the service worker;
    // `must-revalidate` with no max-age means a browser or CDN still asks before reusing one.
    // Everything else keeps Next's own private, no-store default.
    const revalidate = [{ key: "Cache-Control", value: "public, max-age=0, must-revalidate" }];
    const locales = "(en|ha|ig|yo)";

    return [
      { source: "/:path*", headers: SECURITY_HEADERS },
      { source: `/:locale${locales}`, headers: revalidate },
      { source: `/:locale${locales}/projects`, headers: revalidate },
      { source: `/:locale${locales}/projects/:slug`, headers: revalidate },
      { source: `/:locale${locales}/projects/:slug/sources/:sourceId`, headers: revalidate },
      { source: `/:locale${locales}/trust`, headers: revalidate },
      { source: `/:locale${locales}/offline`, headers: revalidate },
      {
        // The worker itself is never cached by the HTTP cache, so an update is seen promptly.
        source: "/:file(sw.js|sw-policy.js)",
        headers: [
          { key: "Cache-Control", value: "no-cache" },
          { key: "Service-Worker-Allowed", value: "/" }
        ]
      }
    ];
  }
};

export default withNextIntl(nextConfig);
