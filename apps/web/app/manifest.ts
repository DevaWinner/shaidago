import type { MetadataRoute } from "next";

/**
 * The web app manifest: real names, the approved canvas colour for both the theme and the
 * background, and a start address that the locale proxy resolves to the visitor's language. There
 * are deliberately no icons: `docs/FRONTEND_VISUAL_DIRECTION.md` authorises no logo or raster asset,
 * so a purpose-made icon set needs a maintainer-approved design before the app can be installed.
 * Installing is optional and nothing depends on it.
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
    categories: ["government", "utilities"]
  };
}
