import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

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
