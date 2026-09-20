/** How long a browser read may take before it is treated as a failed attempt the reader can retry. */
export const CLIENT_READ_TIMEOUT_MS = 10_000;

/**
 * An abort signal that fires when the caller aborts or the time runs out, whichever is first.
 * `AbortSignal.any` and `AbortSignal.timeout` are used when present; otherwise a timer stands in,
 * so an older browser still gets a bounded request rather than one that can hang forever.
 */
export function withTimeout(
  signal: AbortSignal | undefined,
  milliseconds: number = CLIENT_READ_TIMEOUT_MS
): AbortSignal {
  if (typeof AbortSignal.timeout === "function" && typeof AbortSignal.any === "function") {
    const deadline = AbortSignal.timeout(milliseconds);

    return signal === undefined ? deadline : AbortSignal.any([signal, deadline]);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, milliseconds);

  controller.signal.addEventListener("abort", () => {
    clearTimeout(timer);
  });
  signal?.addEventListener("abort", () => {
    controller.abort();
  });

  return controller.signal;
}
