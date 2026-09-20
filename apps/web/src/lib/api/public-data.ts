import "server-only";

import { unstable_cache } from "next/cache";

import { serverApi, PUBLIC_CACHE_TAG, type ApiResult } from "@/lib/api/server";
import type { components } from "@/lib/api/generated/schema";
import { apiQuery, type DirectoryFilters } from "@/lib/directory/filters";
import type { ApiLocale } from "@/lib/api/forwarded-context";

export type ProjectSummary = components["schemas"]["ProjectSummaryOut"];
export type Locality = components["schemas"]["LocalityOut"];

export type PublicRead<T> =
  | { readonly state: "ok"; readonly data: T }
  | { readonly state: "invalid_cursor" }
  | { readonly state: "unavailable"; readonly requestId: string | undefined };

export type ProjectPage = Readonly<{ items: readonly ProjectSummary[]; nextCursor: string | null }>;

/** Thrown inside a cached function so that a failure is never stored as if it were data. */
class PublicReadFailure extends Error {
  public constructor(
    public readonly kind: "invalid_cursor" | "unavailable",
    public readonly requestId: string | undefined
  ) {
    super(kind);
    this.name = "PublicReadFailure";
  }
}

function requestIdOf(result: ApiResult<unknown>): string | undefined {
  return result.kind === "problem"
    ? result.problem.requestId
    : "requestId" in result
      ? result.requestId
      : undefined;
}

const FRESH_SECONDS = 60;

// Why a wrapper and not just `fetch` caching: Next refuses to cache a fetch that carries an
// `Authorization` header once the route is dynamic, whatever `revalidate` says. The internal service
// credential must be sent, so the parsed result is cached here instead. The key is the function
// arguments (language and filters), the tag lets one call drop everything after a publication, and
// only successful reads are stored: failures throw and are never cached. Only the four public
// catalogue reads are wrapped; report, tracking, handle, and reviewer calls never touch this cache.
const cachedLocalities = unstable_cache(
  async (language: ApiLocale) => {
    const result = await serverApi().getLocalities({ locale: language });

    if (result.kind !== "ok") {
      throw new PublicReadFailure("unavailable", requestIdOf(result));
    }

    return result.data.items;
  },
  ["public-localities"],
  { revalidate: FRESH_SECONDS, tags: [PUBLIC_CACHE_TAG] }
);

const cachedProjectPage = unstable_cache(
  async (filters: DirectoryFilters, language: ApiLocale, limit: number | undefined) => {
    const result = await serverApi().listProjects(apiQuery(filters, limit), { locale: language });

    if (result.kind === "problem" && result.problem.code === "invalid_cursor") {
      throw new PublicReadFailure("invalid_cursor", result.problem.requestId);
    }
    if (result.kind !== "ok") {
      throw new PublicReadFailure("unavailable", requestIdOf(result));
    }

    return { items: result.data.items, nextCursor: result.data.next_cursor };
  },
  ["public-project-page"],
  { revalidate: FRESH_SECONDS, tags: [PUBLIC_CACHE_TAG] }
);

async function guarded<T>(read: () => Promise<T>): Promise<PublicRead<T>> {
  try {
    return { state: "ok", data: await read() };
  } catch (error) {
    if (error instanceof PublicReadFailure) {
      return error.kind === "invalid_cursor"
        ? { state: "invalid_cursor" }
        : { state: "unavailable", requestId: error.requestId };
    }

    // An unexpected error is an outage as far as the visitor is concerned; nothing is echoed.
    return { state: "unavailable", requestId: undefined };
  }
}

/**
 * Public catalogue reads for Server Components. Each returns a small state rather than throwing, so
 * a page can keep its product content when the API is down.
 */
export function loadLocalities(language: ApiLocale): Promise<PublicRead<readonly Locality[]>> {
  return guarded(() => cachedLocalities(language));
}

export function loadProjectPage(
  filters: DirectoryFilters,
  language: ApiLocale,
  limit?: number
): Promise<PublicRead<ProjectPage>> {
  return guarded(() => cachedProjectPage(filters, language, limit));
}
