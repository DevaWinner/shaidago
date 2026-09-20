import type { operations } from "@/lib/api/generated/schema";

export const QUEUE_STATUSES = [
  "received",
  "needs_information",
  "under_review",
  "verified_for_public_update",
  "referred",
  "closed"
] as const;
export const QUEUE_RISKS = ["standard", "elevated", "high"] as const;
export const QUEUE_CATEGORIES = [
  "no_visible_work",
  "incomplete_work",
  "unsafe_construction",
  "suspected_incorrect_status",
  "access_barrier",
  "other_concern"
] as const;

export type QueueStatus = (typeof QUEUE_STATUSES)[number];
export type QueueRisk = (typeof QUEUE_RISKS)[number];
export type QueueCategory = (typeof QUEUE_CATEGORIES)[number];

export type QueueFilters = Readonly<{
  status?: QueueStatus;
  risk?: QueueRisk;
  category?: QueueCategory;
  project?: string;
  cursor?: string;
}>;

type Search = Readonly<Record<string, string | readonly string[] | undefined>>;

const PROJECT = /^[a-z0-9-]{1,120}$/;
const CURSOR = /^[\x21-\x7e]{1,512}$/;
const PAGE_SIZE = 20;

function single(value: string | readonly string[] | undefined): string | undefined {
  return typeof value === "string" && value !== "" ? value : undefined;
}

function oneOf<T extends string>(allowed: readonly T[], value: string | undefined): T | undefined {
  return allowed.find((item) => item === value);
}

/**
 * Reads the queue's shareable state from the address. Every value is checked against the API's own
 * enumerations or pattern and anything else is dropped, never passed through, so a crafted link
 * cannot reach the private API with an arbitrary parameter. Only triage filters live in the
 * address; a report's content, contact, or note text never does.
 */
export function parseQueueFilters(search: Search): QueueFilters {
  const project = single(search["project"]);
  const cursor = single(search["cursor"]);
  const status = oneOf(QUEUE_STATUSES, single(search["status"]));
  const risk = oneOf(QUEUE_RISKS, single(search["risk"]));
  const category = oneOf(QUEUE_CATEGORIES, single(search["category"]));

  return {
    ...(status === undefined ? {} : { status }),
    ...(risk === undefined ? {} : { risk }),
    ...(category === undefined ? {} : { category }),
    ...(project !== undefined && PROJECT.test(project) ? { project } : {}),
    ...(cursor !== undefined && CURSOR.test(cursor) ? { cursor } : {})
  };
}

export function hasFilters(filters: QueueFilters): boolean {
  return (
    filters.status !== undefined ||
    filters.risk !== undefined ||
    filters.category !== undefined ||
    filters.project !== undefined
  );
}

type QueueQuery = NonNullable<operations["reviewer_reports_queue"]["parameters"]["query"]>;

export function queueQuery(filters: QueueFilters): QueueQuery {
  return {
    limit: PAGE_SIZE,
    ...(filters.status === undefined ? {} : { status: [filters.status] }),
    ...(filters.risk === undefined ? {} : { risk_level: filters.risk }),
    ...(filters.category === undefined ? {} : { concern_category: filters.category }),
    ...(filters.project === undefined ? {} : { project: filters.project }),
    ...(filters.cursor === undefined ? {} : { cursor: filters.cursor })
  };
}

/** The address of a queue page: filters in a stable order, cursor only when asked for. */
export function queueHref(
  base: string,
  filters: QueueFilters,
  options: { cursor?: string } = {}
): string {
  const parameters = new URLSearchParams();

  for (const name of ["status", "risk", "category", "project"] as const) {
    const value = filters[name];

    if (value !== undefined) {
      parameters.set(name, value);
    }
  }
  if (options.cursor !== undefined) {
    parameters.set("cursor", options.cursor);
  }

  const query = parameters.toString();

  return query === "" ? base : `${base}?${query}`;
}
