/**
 * The API owns run creation, scope, status transitions, and every review decision. This module
 * only turns its documented status values into safe UI behaviour: it never derives progress or
 * grants a discovery action from client state.
 */
export const DISCOVERY_STATUSES = [
  "queued",
  "searching",
  "analysing",
  "needs_review",
  "complete",
  "failed",
  "cancelled"
] as const;

export type DiscoveryStatus = (typeof DISCOVERY_STATUSES)[number];
export type DiscoveryScope = "public" | "reviewer";
export type DiscoveryAction = "poll" | "cancel" | "review";

export type DiscoveryRunIdentity = Readonly<{
  runId: string;
  scope: DiscoveryScope;
  version: number;
}>;

export type RunMemoryPolicy = Readonly<{
  cacheControl: "no-store";
  persistence: "never";
  resume: "current-surface-memory-only";
}>;

/** Public and report-scoped runs never share an in-memory cache key or a navigation hand-off. */
export const RUN_MEMORY_POLICY: Readonly<Record<DiscoveryScope, RunMemoryPolicy>> = {
  public: {
    cacheControl: "no-store",
    persistence: "never",
    resume: "current-surface-memory-only"
  },
  reviewer: {
    cacheControl: "no-store",
    persistence: "never",
    resume: "current-surface-memory-only"
  }
};

const ACTIVE_STATUSES: ReadonlySet<DiscoveryStatus> = new Set(["queued", "searching", "analysing"]);
const PUBLIC_TERMINAL_STATUSES: ReadonlySet<DiscoveryStatus> = new Set([
  "complete",
  "failed",
  "cancelled"
]);
const REVIEWER_TERMINAL_STATUSES: ReadonlySet<DiscoveryStatus> = new Set([
  "needs_review",
  "complete",
  "failed",
  "cancelled"
]);

/** The documented 2s → 3s → 5s → 8s → 10s polling schedule. */
export const POLL_DELAYS_MS = [2_000, 3_000, 5_000, 8_000, 10_000] as const;

export function isDiscoveryStatus(value: string): value is DiscoveryStatus {
  return (DISCOVERY_STATUSES as readonly string[]).includes(value);
}

/**
 * An unknown server status fails closed: it must not leave a timer running or unlock an action.
 * `needs_review` is terminal for a reviewer but stays observable for a public run as documented.
 */
export function shouldPoll(scope: DiscoveryScope, status: string): boolean {
  if (!isDiscoveryStatus(status)) {
    return false;
  }

  return scope === "public"
    ? !PUBLIC_TERMINAL_STATUSES.has(status)
    : !REVIEWER_TERMINAL_STATUSES.has(status);
}

/**
 * Only reviewers have a cancellation operation. A cancellation request is not a terminal result,
 * so its current run continues polling until the API reports a terminal status.
 */
export function allowedDiscoveryActions(
  scope: DiscoveryScope,
  status: string,
  cancelRequested: boolean
): readonly DiscoveryAction[] {
  if (!isDiscoveryStatus(status)) {
    return [];
  }

  if (scope === "reviewer" && status === "needs_review") {
    return ["review"];
  }

  if (ACTIVE_STATUSES.has(status)) {
    if (scope === "reviewer" && !cancelRequested) {
      return ["poll", "cancel"];
    }
    return ["poll"];
  }

  return [];
}

/** A positive Retry-After is authoritative; otherwise use the bounded documented schedule. */
export function nextPollDelayMs(attempt: number, retryAfterSeconds?: number): number {
  if (
    Number.isInteger(retryAfterSeconds) &&
    retryAfterSeconds !== undefined &&
    retryAfterSeconds > 0
  ) {
    return retryAfterSeconds * 1_000;
  }

  const safeAttempt = Number.isInteger(attempt) && attempt > 0 ? attempt : 0;
  const index = Math.min(safeAttempt, POLL_DELAYS_MS.length - 1);

  return POLL_DELAYS_MS[index] ?? POLL_DELAYS_MS[POLL_DELAYS_MS.length - 1]!;
}

/** A delayed or cross-scope response cannot overwrite the current panel's run snapshot. */
export function isNewerRunSnapshot(
  current: DiscoveryRunIdentity,
  candidate: DiscoveryRunIdentity
): boolean {
  return (
    current.scope === candidate.scope &&
    current.runId === candidate.runId &&
    Number.isInteger(candidate.version) &&
    candidate.version > current.version
  );
}
