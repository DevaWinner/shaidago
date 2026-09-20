/** A record whose last check is older than this is labelled, never hidden. */
export const STALE_AFTER_DAYS = 90;

const DAY_MS = 24 * 60 * 60 * 1000;

/** Whole days from a calendar date (YYYY-MM-DD) to `now`, or undefined when there is no date. */
export function daysSinceChecked(lastChecked: string | null, now: Date): number | undefined {
  if (lastChecked === null) {
    return undefined;
  }

  const checked = new Date(`${lastChecked}T00:00:00Z`);

  if (Number.isNaN(checked.getTime())) {
    return undefined;
  }

  return Math.max(0, Math.floor((now.getTime() - checked.getTime()) / DAY_MS));
}

export function isStale(lastChecked: string | null, now: Date): boolean {
  const days = daysSinceChecked(lastChecked, now);

  return days !== undefined && days > STALE_AFTER_DAYS;
}
