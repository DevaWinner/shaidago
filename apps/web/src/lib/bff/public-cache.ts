import "server-only";

import { revalidateTag } from "next/cache";

import { PUBLIC_CACHE_TAG } from "@/lib/api/server";

/**
 * Drops every cached public catalogue read, so a page shows a newly published update on the next
 * request instead of after the freshness window. Only public reads are ever in that cache (report,
 * tracking, handle, and reviewer calls opt out with `no-store`), so nothing private can be flushed
 * or exposed by it. Expiry is immediate: a reviewer who just published expects to see it.
 */
export function revalidatePublicCatalogue(): void {
  revalidateTag(PUBLIC_CACHE_TAG, { expire: 0 });
}
