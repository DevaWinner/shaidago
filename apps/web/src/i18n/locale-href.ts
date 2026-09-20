import type { ApiLocale } from "@/lib/api/forwarded-context";

/**
 * A cursor is only valid for the same filters and locale (API contract), so a language switch
 * starts again from the first page. Every other allowlisted filter is preserved.
 */
const DROPPED_ON_SWITCH: ReadonlySet<string> = new Set(["cursor"]);

export type RouteState = Readonly<{
  /** Path segments below the locale, taken from route params, not from the raw URL. */
  segments?: readonly string[];
  /** Query parameters the page has parsed; only names in `keep` survive. */
  search?: Readonly<Record<string, string | readonly string[] | undefined>>;
  /** The filter names this route treats as shareable state. */
  keep?: readonly string[];
}>;

/**
 * The URL of the equivalent page in another language. It is built from parsed route state, never
 * from the incoming URL string, so it cannot carry an arbitrary redirect target. It never contains
 * report text, a tracking code, contact details, or a draft: only the route and its public filters.
 */
export function localeHref(target: ApiLocale, route: RouteState = {}): string {
  const path = (route.segments ?? []).map((segment) => encodeURIComponent(segment)).join("/");
  const parameters = new URLSearchParams();

  for (const name of route.keep ?? []) {
    if (DROPPED_ON_SWITCH.has(name)) {
      continue;
    }

    const value = route.search?.[name];

    for (const item of typeof value === "string" ? [value] : (value ?? [])) {
      if (item !== "") {
        parameters.append(name, item);
      }
    }
  }

  const query = parameters.toString();

  return `/${target}${path === "" ? "" : `/${path}`}${query === "" ? "" : `?${query}`}`;
}
