import type { BrowserContext } from "@playwright/test";

/** The fictional session the mock API accepts (see `mock-reviewer.mjs`). Not a secret. */
export const SESSION_TOKEN = "fictional-session-token-0123456789abcdef";
export const CSRF_TOKEN = "fictional-csrf-token-0123456789abcdef0";
export const STALE_TOKEN = "fictional-stale-session-0123456789abcd";

/** Signs a browser context in as the fictional reviewer without going through the form. */
export async function signInAs(
  context: BrowserContext,
  baseURL: string,
  session: string = SESSION_TOKEN
): Promise<void> {
  await context.addCookies(
    [
      ["sg_session", session],
      ["sg_csrf", CSRF_TOKEN]
    ].map(([name, value]) => ({
      name: name as string,
      value: value as string,
      url: baseURL,
      httpOnly: true,
      sameSite: "Lax" as const
    }))
  );
}
