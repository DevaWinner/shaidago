import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import proxy, { config } from "../../proxy";
import { LOCALES, REVIEWED_LOCALES, contentLocale, isSupportedLocale } from "@/i18n/routing";

const origin = "https://shaidago.example";

function visit(path: string, headers: Record<string, string> = {}) {
  return proxy(new NextRequest(`${origin}${path}`, { headers }));
}

function location(response: Response): URL | undefined {
  const value = response.headers.get("location");

  return value === null ? undefined : new URL(value, origin);
}

describe("locale negotiation", () => {
  it("sends a bare visit to English when nothing else is known", async () => {
    const response = await visit("/");

    expect(location(response)?.pathname).toBe("/en");
    expect([301, 302, 307, 308]).toContain(response.status);
  });

  it("prefers the language cookie, then Accept-Language, and ignores everything else", async () => {
    expect(location(await visit("/", { cookie: "NEXT_LOCALE=yo" }))?.pathname).toBe("/yo");
    expect(location(await visit("/", { "accept-language": "ha,en;q=0.5" }))?.pathname).toBe("/ha");
    expect(
      location(await visit("/", { cookie: "NEXT_LOCALE=ig", "accept-language": "ha" }))?.pathname
    ).toBe("/ig");
    expect(location(await visit("/", { "accept-language": "fr-FR,de;q=0.8" }))?.pathname).toBe(
      "/en"
    );
  });

  it("ignores an unsupported or hostile cookie value", async () => {
    for (const value of ["fr", "EN", "../../etc", "%2F%2Fevil.example", ""]) {
      const response = await visit("/", { cookie: `NEXT_LOCALE=${value}` });

      expect(location(response)?.pathname, value).toBe("/en");
      expect(location(response)?.origin, value).toBe(origin);
    }
  });

  it("keeps the path and query when adding the prefix", async () => {
    const target = location(await visit("/projects?locality=amac&q=clinic&cursor=abc%3D"));

    expect(target?.pathname).toBe("/en/projects");
    expect(target?.search).toBe("?locality=amac&q=clinic&cursor=abc%3D");
  });

  it("serves an already prefixed route and remembers the choice in a harmless cookie", async () => {
    const response = await visit("/ha");

    expect(response.status).toBe(200);
    const cookie = response.headers
      .getSetCookie()
      .find((entry) => entry.startsWith("NEXT_LOCALE="));
    expect(cookie).toMatch(/^NEXT_LOCALE=ha;/);
    expect(cookie).toMatch(/SameSite=lax/i);
    expect(cookie).toMatch(/Max-Age=31536000/);
    expect(cookie).not.toMatch(/Domain=/i);
  });

  it("treats an unsupported first segment as a path, never as a redirect target", async () => {
    // A differently cased real locale is canonicalised to the lower-case prefix.
    expect(location(await visit("/EN"))?.pathname).toBe("/en");

    for (const path of ["/xx/foo", "/english", "/ha-NG/x"]) {
      const target = location(await visit(path));

      expect(target?.origin, path).toBe(origin);
      expect(target?.pathname.startsWith("/en/"), path).toBe(true);
    }
  });

  it("cannot be turned into an open redirect", async () => {
    for (const path of [
      "//evil.example",
      "//evil.example/x",
      "/\\evil.example",
      "/%2F%2Fevil.example",
      "/%5Cevil.example",
      "/https://evil.example",
      "/.evil.example"
    ]) {
      const response = await visit(path);
      const target = location(response);

      expect(target === undefined || target.origin === origin, path).toBe(true);
      // A redirect target that starts with two slashes or a scheme would leave this origin.
      const raw = response.headers.get("location") ?? "/";
      expect(
        raw.startsWith("//") || raw.startsWith("http://evil") || raw.startsWith("https://evil"),
        path
      ).toBe(false);
    }
  });

  it("excludes the BFF, the health routes, framework assets, and files from negotiation by matcher", () => {
    // Behaviour (API routes and /robots.txt answer unprefixed) is proven in the browser suite.
    expect(config.matcher).toEqual(["/((?!api|health|_next|_vercel|.*\\..*).*)"]);
  });
});

describe("locale configuration", () => {
  it("names exactly the four public locales and keeps English the default", () => {
    expect([...LOCALES]).toEqual(["en", "ha", "ig", "yo"]);
    expect(isSupportedLocale("ha")).toBe(true);
    for (const value of ["fr", "EN", "", undefined, null, 5]) {
      expect(isSupportedLocale(value)).toBe(false);
    }
  });

  it("serves each locale in its own language because every critical domain is reviewed", () => {
    expect([...REVIEWED_LOCALES]).toEqual(["en", "ha", "ig", "yo"]);
    for (const locale of LOCALES) {
      expect(contentLocale(locale)).toBe(locale);
    }
  });
});
