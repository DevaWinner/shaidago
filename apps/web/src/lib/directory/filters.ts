import type { operations } from "@/lib/api/generated/schema";

type ListQuery = NonNullable<operations["projects_list"]["parameters"]["query"]>;

export const CATEGORIES = [
  "health",
  "education",
  "water_sanitation",
  "roads_public_works",
  "other_public_service"
] as const satisfies readonly NonNullable<ListQuery["category"]>[];

export const STATUSES = [
  "unknown",
  "planned",
  "procurement",
  "in_progress",
  "on_hold",
  "completed",
  "cancelled"
] as const satisfies readonly NonNullable<ListQuery["status"]>[];

export const VERIFICATIONS = [
  "awaiting_verification",
  "verified_official",
  "corroborated",
  "community_reviewed",
  "disputed",
  "outdated"
] as const satisfies readonly NonNullable<ListQuery["verification"]>[];

// A compile error here means the API gained a value this module does not know about.
type Exhaustive<Allowed, All> = [Exclude<All, Allowed>] extends [never] ? true : never;
export const _exhaustive: [
  Exhaustive<(typeof CATEGORIES)[number], NonNullable<ListQuery["category"]>>,
  Exhaustive<(typeof STATUSES)[number], NonNullable<ListQuery["status"]>>,
  Exhaustive<(typeof VERIFICATIONS)[number], NonNullable<ListQuery["verification"]>>
] = [true, true, true];

export const PAGE_SIZE = 12;
export const MAX_QUERY_LENGTH = 100;
const MAX_CURSOR_LENGTH = 512;
const SLUG_LIKE = /^[a-z0-9-]{1,80}$/;
// A cursor is opaque; only its transport-safe alphabet is checked, never its meaning.
const CURSOR_ALPHABET = /^[A-Za-z0-9._~=-]+$/;

export type DirectoryFilters = Readonly<{
  q?: string;
  locality?: string;
  category?: (typeof CATEGORIES)[number];
  status?: (typeof STATUSES)[number];
  verification?: (typeof VERIFICATIONS)[number];
  cursor?: string;
}>;

export type RawSearchParams = Readonly<Record<string, string | readonly string[] | undefined>>;

/** Filters that narrow results, in the canonical order they are written to a URL. */
export const FILTER_NAMES = ["q", "locality", "category", "status", "verification"] as const;
export type FilterName = (typeof FILTER_NAMES)[number];
const ALL_NAMES = [...FILTER_NAMES, "cursor"] as const;

function first(value: string | readonly string[] | undefined): string | undefined {
  return typeof value === "string" ? value : value?.[0];
}

function oneOf<T extends string>(allowed: readonly T[], value: string | undefined): T | undefined {
  return allowed.find((candidate) => candidate === value);
}

export function normaliseQuery(value: string | undefined): string | undefined {
  const text = (value ?? "")
    .normalize("NFC")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_QUERY_LENGTH)
    .trim();

  return text === "" ? undefined : text;
}

export type ParsedFilters = Readonly<{
  filters: DirectoryFilters;
  /** True when the incoming URL differs from the canonical one, so the page should redirect. */
  needsCanonicalRedirect: boolean;
}>;

/**
 * Parses shareable state from the URL. Only known names and allowlisted values survive: an unknown
 * locality, enum value, malformed cursor, repeated parameter, or unrecognised name is dropped, so
 * nothing the visitor types can become a backend filter.
 */
export function parseFilters(
  params: RawSearchParams,
  knownLocalities: readonly string[]
): ParsedFilters {
  const locality = first(params["locality"]);
  const cursor = first(params["cursor"]);
  const q = normaliseQuery(first(params["q"]));
  const category = oneOf(CATEGORIES, first(params["category"]));
  const status = oneOf(STATUSES, first(params["status"]));
  const verification = oneOf(VERIFICATIONS, first(params["verification"]));

  const filters: DirectoryFilters = {
    ...(q === undefined ? {} : { q }),
    ...(locality !== undefined && SLUG_LIKE.test(locality) && knownLocalities.includes(locality)
      ? { locality }
      : {}),
    ...(category === undefined ? {} : { category }),
    ...(status === undefined ? {} : { status }),
    ...(verification === undefined ? {} : { verification }),
    ...(cursor !== undefined && cursor.length <= MAX_CURSOR_LENGTH && CURSOR_ALPHABET.test(cursor)
      ? { cursor }
      : {})
  };

  const canonical = new URLSearchParams(toQueryString(filters, { cursor: true }));
  const incoming = Object.entries(params).flatMap(([name, value]) =>
    (typeof value === "string" ? [value] : (value ?? [])).map((item) => [name, item] as const)
  );
  const differs =
    incoming.length !== [...canonical].length ||
    incoming.some(([name, value]) => canonical.get(name) !== value);

  return { filters, needsCanonicalRedirect: differs };
}

/** The canonical query string: fixed order, no empty values, cursor only when asked for. */
export function toQueryString(filters: DirectoryFilters, options: { cursor: boolean }): string {
  const parameters = new URLSearchParams();

  for (const name of ALL_NAMES) {
    const value = filters[name];

    if (value !== undefined && (name !== "cursor" || options.cursor)) {
      parameters.set(name, value);
    }
  }

  return parameters.toString();
}

/** The path for a filter set, always without a fragment; `withResults` adds the results anchor. */
export function directoryHref(
  locale: string,
  filters: DirectoryFilters,
  options: { cursor?: boolean; withResults?: boolean } = {}
): string {
  const query = toQueryString(filters, { cursor: options.cursor ?? false });

  return `/${locale}/projects${query === "" ? "" : `?${query}`}${options.withResults === true ? "#results" : ""}`;
}

/** The same filters without one of them (and always without a cursor, which depends on the set). */
export function withoutFilter(filters: DirectoryFilters, name: FilterName): DirectoryFilters {
  return Object.fromEntries(
    Object.entries(filters).filter(([key]) => key !== name && key !== "cursor")
  ) as DirectoryFilters;
}

export function activeFilterNames(filters: DirectoryFilters): readonly FilterName[] {
  return FILTER_NAMES.filter((name) => filters[name] !== undefined);
}

/** The bounded API query for a filter set. Only allowlisted values ever reach the backend. */
export function apiQuery(filters: DirectoryFilters, limit: number = PAGE_SIZE): ListQuery {
  return {
    limit,
    ...(filters.q === undefined ? {} : { q: filters.q }),
    ...(filters.locality === undefined ? {} : { locality: filters.locality }),
    ...(filters.category === undefined ? {} : { category: filters.category }),
    ...(filters.status === undefined ? {} : { status: filters.status }),
    ...(filters.verification === undefined ? {} : { verification: filters.verification }),
    ...(filters.cursor === undefined ? {} : { cursor: filters.cursor })
  };
}
