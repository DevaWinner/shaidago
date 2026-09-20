import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DRAFT_TTL_MS,
  clearDraft,
  draftStorageAvailable,
  loadDraft,
  saveDraft
} from "@/lib/report/draft";

class MemoryStorage {
  data = new Map<string, string>();
  get length() {
    return this.data.size;
  }
  getItem(key: string) {
    return this.data.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.data.set(key, value);
  }
  removeItem(key: string) {
    this.data.delete(key);
  }
}

let store: MemoryStorage;
const NOW = 1_800_000_000_000;

beforeEach(() => {
  store = new MemoryStorage();
  vi.stubGlobal("window", { localStorage: store });
});

const values = { category: "unsafe_construction", description: "A wall is leaning." } as const;

describe("report draft", () => {
  it("saves only the concern, description, step, and project, and reads them back for that project", () => {
    expect(saveDraft("p1", "anonymity", values, NOW)).toBe(true);

    const raw = JSON.parse(store.getItem("shaidago.report-draft") ?? "{}") as Record<
      string,
      unknown
    >;

    expect(Object.keys(raw).sort()).toEqual(
      ["category", "description", "project", "savedAt", "step", "version"].sort()
    );
    expect(loadDraft("p1", NOW + 1000)).toMatchObject({ step: "anonymity", ...values });
    // A draft for another project is not offered, and is not deleted.
    expect(loadDraft("p2", NOW + 1000)).toBeUndefined();
    expect(store.length).toBe(1);
  });

  it("never lands on the notice step", () => {
    saveDraft("p1", "notice", values, NOW);

    expect(loadDraft("p1", NOW)?.step).toBe("observation");
  });

  it("expires after 24 hours and deletes what expired", () => {
    saveDraft("p1", "review", values, NOW);

    expect(loadDraft("p1", NOW + DRAFT_TTL_MS - 1)).toBeDefined();
    expect(loadDraft("p1", NOW + DRAFT_TTL_MS)).toBeUndefined();
    expect(store.length).toBe(0);
  });

  it.each([
    ["corrupt JSON", "{not json"],
    [
      "a wrong version",
      JSON.stringify({
        version: 0,
        savedAt: NOW,
        project: "p1",
        step: "review",
        category: "",
        description: ""
      })
    ],
    [
      "a future date",
      JSON.stringify({
        version: 1,
        savedAt: NOW + 99999,
        project: "p1",
        step: "review",
        category: "",
        description: ""
      })
    ],
    [
      "a bad step",
      JSON.stringify({
        version: 1,
        savedAt: NOW,
        project: "p1",
        step: "notice",
        category: "",
        description: ""
      })
    ],
    [
      "a bad category",
      JSON.stringify({
        version: 1,
        savedAt: NOW,
        project: "p1",
        step: "review",
        category: "nope",
        description: ""
      })
    ],
    ["a non-object", "5"]
  ])("deletes %s instead of trusting it", (_name, raw) => {
    store.setItem("shaidago.report-draft", raw);

    expect(loadDraft("p1", NOW)).toBeUndefined();
    expect(store.length).toBe(0);
  });

  it("can be cleared, and reports nothing saved when storage is empty", () => {
    expect(loadDraft("p1", NOW)).toBeUndefined();
    saveDraft("p1", "review", values, NOW);
    clearDraft();
    expect(store.length).toBe(0);
  });

  it("copes with unavailable, full, or blocked storage without throwing", () => {
    vi.stubGlobal("window", undefined);
    expect(draftStorageAvailable()).toBe(false);
    expect(saveDraft("p1", "review", values, NOW)).toBe(false);
    expect(loadDraft("p1", NOW)).toBeUndefined();
    clearDraft();

    const throwing = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("full");
      },
      removeItem: () => {
        throw new Error("blocked");
      }
    };
    vi.stubGlobal("window", { localStorage: throwing });
    expect(draftStorageAvailable()).toBe(false);
    expect(saveDraft("p1", "review", values, NOW)).toBe(false);
    expect(loadDraft("p1", NOW)).toBeUndefined();
    clearDraft();

    vi.stubGlobal("window", {
      get localStorage(): never {
        throw new Error("denied");
      }
    });
    expect(draftStorageAvailable()).toBe(false);
  });

  it("detects working storage", () => {
    expect(draftStorageAvailable()).toBe(true);
    expect(store.length).toBe(0);
  });
});
