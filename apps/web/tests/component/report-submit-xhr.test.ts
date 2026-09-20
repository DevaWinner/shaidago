import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_FORM } from "@/lib/report/flow";
import { submitReport } from "@/lib/report/submit";

class FakeXhr {
  static last: FakeXhr | undefined;
  headers: Record<string, string> = {};
  upload: {
    onprogress?: (event: { lengthComputable: boolean; loaded: number; total: number }) => void;
  } = {};
  status = 0;
  responseText = "";
  responseHeaders = "";
  onload?: () => void;
  onerror?: () => void;
  onabort?: () => void;
  ontimeout?: () => void;
  method = "";
  url = "";
  sent: unknown;
  open(method: string, url: string) {
    this.method = method;
    this.url = url;
    FakeXhr.last = this;
  }
  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }
  getAllResponseHeaders() {
    return this.responseHeaders;
  }
  send(body: unknown) {
    this.sent = body;
  }
  abort() {
    this.onabort?.();
  }
}

const input = {
  slug: "p-1",
  form: {
    ...EMPTY_FORM,
    category: "other_concern",
    description: "A fictional concern here."
  } as const,
  files: []
};
const run = (signal = new AbortController().signal, onProgress = vi.fn()) =>
  submitReport({
    input,
    idempotencyKey: "0198f1a2-7b3c-4d4e-8f5a-123456789abc",
    locale: "ha",
    onProgress,
    signal
  });
const receipt = JSON.stringify({
  attachments: [],
  contact_saved: false,
  next_steps: ["save_tracking_code"],
  published: false,
  status: "received",
  tracking_code: "SG-DEMO-0001"
});

afterEach(() => {
  vi.unstubAllGlobals();
  FakeXhr.last = undefined;
});

describe("submitReport", () => {
  it("posts the multipart body to the fixed same-origin path with the key and locale", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
    const pending = run();
    const xhr = FakeXhr.last as FakeXhr;

    expect(xhr.method).toBe("POST");
    expect(xhr.url).toBe("/api/reports");
    expect(xhr.headers["Idempotency-Key"]).toBe("0198f1a2-7b3c-4d4e-8f5a-123456789abc");
    expect(xhr.headers["X-Shaidago-Locale"]).toBe("ha");
    expect(xhr.sent).toBeInstanceOf(FormData);
    xhr.status = 201;
    xhr.responseText = receipt;
    xhr.responseHeaders = "Idempotency-Replayed: true\r\nContent-Type: application/json";
    xhr.onload?.();

    expect(await pending).toMatchObject({ kind: "received", replayed: true });
  });

  it("reports upload progress as a fraction and ignores an unknown length", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
    const progress = vi.fn();
    const pending = run(undefined, progress);
    const xhr = FakeXhr.last as FakeXhr;

    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 50, total: 200 });
    xhr.upload.onprogress?.({ lengthComputable: false, loaded: 0, total: 0 });
    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 500, total: 200 });
    xhr.onerror?.();

    expect(progress.mock.calls).toEqual([[0.25], [1]]);
    expect(await pending).toEqual({ kind: "network" });
  });

  it("returns the safe problem from an error response and never the raw body", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
    const pending = run();
    const xhr = FakeXhr.last as FakeXhr;

    xhr.status = 429;
    xhr.responseText = JSON.stringify({
      code: "rate_limited",
      detail: "SECRET DETAIL",
      status: 429
    });
    xhr.responseHeaders = "Content-Type: application/problem+json\r\nRetry-After: 30";
    xhr.onload?.();
    const outcome = await pending;

    expect(outcome).toMatchObject({
      kind: "problem",
      problem: { code: "rate_limited", retryAfterSeconds: 30 }
    });
    expect(JSON.stringify(outcome)).not.toContain("SECRET");
  });

  it("treats a 201 with an unreadable body as a problem, and a body-less status without throwing", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
    let pending = run();
    let xhr = FakeXhr.last as FakeXhr;

    xhr.status = 201;
    xhr.responseText = "not json";
    xhr.responseHeaders = "X-Request-Id: 0198f1a2-7b3c-4d4e-8f5a-123456789abc";
    xhr.onload?.();
    expect(await pending).toMatchObject({ kind: "problem", problem: { code: "internal_error" } });

    pending = run();
    xhr = FakeXhr.last as FakeXhr;
    xhr.status = 304;
    xhr.onload?.();
    expect(await pending).toMatchObject({ kind: "problem" });
  });

  it("resolves aborted, network, and timeout distinctly, and never sends if already aborted", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXhr);
    const controller = new AbortController();
    const pending = run(controller.signal);

    controller.abort();
    expect(await pending).toEqual({ kind: "aborted" });

    let again = run();
    (FakeXhr.last as FakeXhr).ontimeout?.();
    expect(await again).toEqual({ kind: "network" });

    FakeXhr.last = undefined;
    const done = new AbortController();
    done.abort();
    again = run(done.signal);
    expect(await again).toEqual({ kind: "aborted" });
    expect(FakeXhr.last).toBeUndefined();
  });
});
