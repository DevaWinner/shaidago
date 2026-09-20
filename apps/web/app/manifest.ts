import type { MetadataRoute } from "next";

/**
 * The web app manifest: real names, the approved canvas colour for the theme and background, and a
 * start address that the locale proxy resolves to the visitor's language. The icons are the simple
 * letter mark the maintainer asked for (`public/icons`, drawn from the approved accent and canvas
 * colours, no external asset). Installing is optional and nothing depends on it.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ShaidaGo",
    short_name: "ShaidaGo",
    description: "Source-backed project records and safer next actions for Abuja communities.",
    id: "/",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "any",
    background_color: "#F7F2E8",
    theme_color: "#F7F2E8",
    lang: "en",
    dir: "ltr",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable"
      },
      { src: "/icons/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }
    ],
    categories: ["government", "utilities"]
  };
}
