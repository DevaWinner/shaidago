import { describe, expect, it, vi } from "vitest";

import { PUBLIC_CACHE_TAG, createServerApi } from "@/lib/api/server";

const id = "0198f1a2-7b3c-4d4e-8f5a-123456789a01";
const opts = { context: { requestId: id } };
const reviewer = { ...opts, session: "s".repeat(32), csrf: "c".repeat(32) };

type Init = RequestInit & { next?: { revalidate?: number; tags?: string[] } };

function harness() {
  const inits: Init[] = [];
  const api = createServerApi({
    environment: {
      appEnvironment: "test",
      apiInternalUrl: "http://api.internal-test.invalid",
      internalWebCredential: "shaida-go-unit-test-credential-not-a-secret",
      clientHmacKey: undefined,
      trustedProxyHops: 1
    },
    fetch: (async (_request: Request, init?: Init) => {
      inits.push(init ?? {});

      return new Response(JSON.stringify({ items: [], next_cursor: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    }) as unknown as typeof fetch,
    sleep: async () => undefined,
    generateRequestId: () => id
  });

  return { api, inits };
}

/** Every public catalogue read, and how to call it. Only these may use the shared data cache. */
const PUBLIC_READS: Record<string, (api: ReturnType<typeof harness>["api"]) => Promise<unknown>> = {
  getLocalities: (api) => api.getLocalities({}),
  listProjects: (api) => api.listProjects({ limit: 1 }, {}),
  getProject: (api) => api.getProject("x", {}),
  getProjectSource: (api) => api.getProjectSource("x", id, {})
};

/** Everything else: private, per-visitor, or a mutation. None may be cached, anywhere. */
const NEVER_CACHED: Record<string, (api: ReturnType<typeof harness>["api"]) => Promise<unknown>> = {
  askQuestion: (api) => api.askQuestion("x", { question: "q" }, opts),
  startPublicDiscovery: (api) => api.startPublicDiscovery("x", opts),
  getPublicDiscoveryRun: (api) => api.getPublicDiscoveryRun(id, undefined, opts),
  submitReport: (api) =>
    api.submitReport(new ReadableStream(), "multipart/form-data; boundary=x", opts),
  lookupReportStatus: (api) => api.lookupReportStatus({ code: "x" }, opts),
  answerFollowUp: (api) =>
    api.answerFollowUp({ question_id: id, kind: "skipped", code: "x" }, opts),
  createReporterHandle: (api) => api.createReporterHandle(opts),
  listHandleReports: (api) => api.listHandleReports({ handle: "h", passphrase: "p" }, opts),
  deleteReporterHandle: (api) => api.deleteReporterHandle({ handle: "h", passphrase: "p" }, opts),
  signIn: (api) => api.signIn({ identifier: "i", password: "p" }, opts),
  signOut: (api) => api.signOut(reviewer),
  listReviewerReports: (api) => api.listReviewerReports({}, reviewer),
  getReviewerReport: (api) => api.getReviewerReport(id, false, reviewer),
  listReviewerNotes: (api) => api.listReviewerNotes(id, {}, reviewer),
  listPublicationDrafts: (api) => api.listPublicationDrafts(id, reviewer),
  getPublicationPreview: (api) => api.getPublicationPreview(id, id, reviewer),
  getReviewerDiscoveryRun: (api) => api.getReviewerDiscoveryRun(id, reviewer),
  downloadEvidence: (api) => api.downloadEvidence(id, id, reviewer),
  createNote: (api) => api.createNote(id, { body: "b" }, reviewer),
  askReviewerFollowUp: (api) => api.askReviewerFollowUp(id, { question: "q" }, reviewer),
  withdrawReviewerFollowUp: (api) => api.withdrawReviewerFollowUp(id, id, reviewer),
  transitionReport: (api) =>
    api.transitionReport(
      id,
      { command: "close", expected_status: "received", expected_version: 1 },
      reviewer
    ),
  createPublicationDraft: (api) => api.createPublicationDraft(id, {} as never, reviewer),
  publishUpdate: (api) => api.publishUpdate(id, id, { preview_digest: "a".repeat(64) }, reviewer),
  withdrawUpdate: (api) => api.withdrawUpdate(id, id, reviewer),
  planDiscovery: (api) => api.planDiscovery(id, { concepts: [] }, reviewer),
  createDiscoveryRun: (api) =>
    api.createDiscoveryRun(id, { approved_digest: "a".repeat(64), concepts: [] }, reviewer),
  cancelDiscoveryRun: (api) => api.cancelDiscoveryRun(id, reviewer),
  reviewDiscoveryRun: (api) => api.reviewDiscoveryRun(id, { command: "reject_run" }, reviewer),
  answerDiscoveryFollowUp: (api) =>
    api.answerDiscoveryFollowUp(id, { question_index: 0, kind: "skipped" }, reviewer),
  decideDiscoveredSource: (api) =>
    api.decideDiscoveredSource(id, { command: "defer", reason: "r" }, reviewer)
};

describe("public data cache policy", () => {
  it("classifies every method of the server API, so a new one must be placed deliberately", () => {
    const methods = Object.keys(harness().api).toSorted();

    expect(methods).toEqual(
      [...Object.keys(PUBLIC_READS), ...Object.keys(NEVER_CACHED)].toSorted()
    );
  });

  it("caches public catalogue reads briefly, under one tag, and nothing else", async () => {
    for (const [name, call] of Object.entries(PUBLIC_READS)) {
      const { api, inits } = harness();

      await call(api);

      expect(inits[0]?.next, name).toEqual({ revalidate: 60, tags: [PUBLIC_CACHE_TAG] });
      expect(inits[0]?.cache, name).toBeUndefined();
    }
  });

  it("never caches a private, per-visitor, or mutating call", async () => {
    for (const [name, call] of Object.entries(NEVER_CACHED)) {
      const { api, inits } = harness();

      await call(api).catch(() => undefined);

      expect(inits[0]?.cache, name).toBe("no-store");
      expect(inits[0]?.next, name).toBeUndefined();
    }
  });
});

describe("publication revalidation", () => {
  it("expires the public tag immediately, and only that tag", async () => {
    const revalidateTag = vi.fn();
    vi.resetModules();
    vi.doMock("next/cache", () => ({ revalidateTag }));

    const { revalidatePublicCatalogue } = await import("@/lib/bff/public-cache");
    revalidatePublicCatalogue();

    expect(revalidateTag).toHaveBeenCalledExactlyOnceWith(PUBLIC_CACHE_TAG, { expire: 0 });
    vi.doUnmock("next/cache");
    vi.resetModules();
  });
});
