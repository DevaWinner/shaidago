/**
 * The one-time receipt, held only in this page's memory. It is never written to storage, a URL, a
 * cookie, or a cache, so it survives a client-side navigation to the confirmation page and nothing
 * else: a reload, a back navigation after leaving, or a direct visit finds it gone.
 */

export type ReceiptAttachment = Readonly<{
  position: number;
  kept: boolean;
  reason: string | null;
}>;

export type Receipt = Readonly<{
  trackingCode: string;
  contactSaved: boolean;
  attachments: readonly ReceiptAttachment[];
  nextSteps: readonly string[];
  /** Whether a reporter handle was used; the passphrase is never kept. */
  handleUsed: boolean;
}>;

let current: Receipt | undefined;
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of listeners) {
    listener();
  }
}

export function setReceipt(receipt: Receipt): void {
  current = receipt;
  notify();
}

export function peekReceipt(): Receipt | undefined {
  return current;
}

export function clearReceipt(): void {
  if (current !== undefined) {
    current = undefined;
    notify();
  }
}

export function subscribeToReceipt(listener: () => void): () => void {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}
