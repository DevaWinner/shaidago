import { STEPS, CATEGORIES, type ConcernCategory, type Step } from "@/lib/report/flow";

/**
 * The optional private draft. It exists only after the person accepts the shared-device warning,
 * holds only the kind of concern, the description, the step, and the project, and expires after
 * 24 hours. Files, contact details, handles, passphrases, tracking codes, and server errors are
 * never accepted here: the type has no place for them. Every storage call is guarded because
 * storage can be missing, full, or disabled in a private window; the wizard works without it.
 */

const KEY = "shaidago.report-draft";
export const DRAFT_VERSION = 1;
export const DRAFT_TTL_MS = 24 * 60 * 60 * 1000;
const DRAFT_STEPS: readonly Step[] = STEPS.filter((step) => step !== "notice");

export type Draft = Readonly<{
  version: typeof DRAFT_VERSION;
  savedAt: number;
  project: string;
  step: Step;
  category: ConcernCategory | "";
  description: string;
}>;

function storage(): Storage | undefined {
  try {
    return typeof window === "undefined" ? undefined : window.localStorage;
  } catch {
    return undefined;
  }
}

let probedStore: Storage | undefined;
let probedResult = false;

/** Whether this browser lets a draft be saved. The probe writes once per storage object, not per call. */
export function draftStorageAvailable(): boolean {
  const store = storage();

  if (store === undefined) {
    return false;
  }
  if (store === probedStore) {
    return probedResult;
  }

  probedStore = store;

  try {
    const probe = `${KEY}.probe`;
    store.setItem(probe, "1");
    store.removeItem(probe);
    probedResult = true;
  } catch {
    probedResult = false;
  }

  return probedResult;
}

const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) {
    listener();
  }
}

/** For `useSyncExternalStore`: the wizard re-reads storage when it changes here or in another tab. */
export function subscribeToDraft(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);

  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

/** The stored text, unparsed, so a snapshot compares by value and never allocates. */
export function readRawDraft(): string | null {
  try {
    return storage()?.getItem(KEY) ?? null;
  } catch {
    return null;
  }
}

export function clearDraft(): void {
  try {
    storage()?.removeItem(KEY);
  } catch {
    // Nothing was stored that could be removed.
  }
  notify();
}

/** Returns false when the draft could not be saved, so the person is told and nothing is implied. */
export function saveDraft(
  project: string,
  step: Step,
  values: Readonly<{ category: ConcernCategory | ""; description: string }>,
  now: number
): boolean {
  const store = storage();

  if (store === undefined) {
    return false;
  }

  const draft: Draft = {
    version: DRAFT_VERSION,
    savedAt: now,
    project,
    step: DRAFT_STEPS.includes(step) ? step : "observation",
    category: values.category,
    description: values.description
  };

  try {
    store.setItem(KEY, JSON.stringify(draft));
    notify();

    return true;
  } catch {
    return false;
  }
}

function isDraft(value: unknown): value is Draft {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const draft = value as Record<string, unknown>;

  return (
    draft["version"] === DRAFT_VERSION &&
    typeof draft["savedAt"] === "number" &&
    Number.isFinite(draft["savedAt"]) &&
    typeof draft["project"] === "string" &&
    typeof draft["description"] === "string" &&
    draft["description"].length <= 8000 &&
    typeof draft["step"] === "string" &&
    (DRAFT_STEPS as readonly string[]).includes(draft["step"]) &&
    (draft["category"] === "" ||
      (CATEGORIES as readonly string[]).includes(draft["category"] as string))
  );
}

export type DraftLookup =
  | Readonly<{ kind: "none" }>
  | Readonly<{ kind: "invalid" }>
  | Readonly<{ kind: "found"; draft: Draft }>;

/**
 * Reads a stored draft without side effects. `invalid` means the stored text is expired, corrupt,
 * of another version, or dated in the future and should be deleted; a draft for a different project
 * is `none` and is left alone until it expires.
 */
export function parseDraft(raw: string | null, project: string, now: number): DraftLookup {
  if (raw === null) {
    return { kind: "none" };
  }

  let parsed: unknown;

  try {
    parsed = JSON.parse(raw);
  } catch {
    return { kind: "invalid" };
  }

  if (!isDraft(parsed) || parsed.savedAt > now || now - parsed.savedAt >= DRAFT_TTL_MS) {
    return { kind: "invalid" };
  }

  return parsed.project === project ? { kind: "found", draft: parsed } : { kind: "none" };
}

/** The saved draft for this project, or undefined; a draft that cannot be used is deleted. */
export function loadDraft(project: string, now: number): Draft | undefined {
  const lookup = parseDraft(readRawDraft(), project, now);

  if (lookup.kind === "invalid") {
    clearDraft();
  }

  return lookup.kind === "found" ? lookup.draft : undefined;
}
