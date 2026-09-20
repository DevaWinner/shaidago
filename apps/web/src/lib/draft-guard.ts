/**
 * A tiny in-memory flag for "this page holds an unsaved private draft". It exists only so the
 * language switch can warn before navigating away. It stores no draft content, nothing is written to
 * browser storage, and it is empty after a reload.
 */

let unsaved = false;
const listeners = new Set<() => void>();

export function setUnsavedDraft(dirty: boolean): void {
  if (unsaved !== dirty) {
    unsaved = dirty;
    for (const listener of listeners) {
      listener();
    }
  }
}

export function hasUnsavedDraft(): boolean {
  return unsaved;
}

export function subscribeToDraft(listener: () => void): () => void {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}
