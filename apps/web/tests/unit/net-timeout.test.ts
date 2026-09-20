import { afterEach, describe, expect, it, vi } from "vitest";

import { CLIENT_READ_TIMEOUT_MS, withTimeout } from "@/lib/net/timeout";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("withTimeout", () => {
  it("aborts when the time runs out, using the platform helpers when present", async () => {
    // The platform timeout is native, so real (short) time is used here.
    const signal = withTimeout(undefined, 30);

    expect(signal.aborted).toBe(false);
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(signal.aborted).toBe(true);
  });

  it("aborts at once when the caller aborts", () => {
    const caller = new AbortController();
    const signal = withTimeout(caller.signal, 60_000);

    caller.abort();
    expect(signal.aborted).toBe(true);
  });

  it("still bounds a request when the browser has no AbortSignal.any or timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("AbortSignal", class extends EventTarget {} as unknown as typeof AbortSignal);
    const stub = globalThis.AbortSignal as unknown as { timeout?: unknown; any?: unknown };

    expect(stub.timeout).toBeUndefined();
    const caller = new AbortController();
    const signal = withTimeout(caller.signal, 100);

    expect(signal.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(120);
    expect(signal.aborted).toBe(true);
  });

  it("defaults to a bounded ten-second wait", () => {
    expect(CLIENT_READ_TIMEOUT_MS).toBe(10_000);
  });
});
