import { describe, expect, it } from "vitest";

import { deriveClientHmac, trustedClientAddress } from "@/lib/bff/request-context";

const key = Buffer.alloc(32, 1);
const day = Date.UTC(2026, 8, 20, 12);

describe("trusted client address", () => {
  it("uses only the entry our own proxies appended, never the client-writable left end", () => {
    expect(trustedClientAddress("203.0.113.9", 1)).toBe("203.0.113.9");
    expect(trustedClientAddress("198.51.100.1, 203.0.113.9", 1)).toBe("203.0.113.9");
    expect(trustedClientAddress("198.51.100.1, 203.0.113.9, 10.0.0.2", 2)).toBe("203.0.113.9");
  });

  it("returns nothing when there is no trustworthy or valid address", () => {
    expect(trustedClientAddress(null, 1)).toBeUndefined();
    expect(trustedClientAddress("203.0.113.9", 0)).toBeUndefined();
    expect(trustedClientAddress("203.0.113.9", 3)).toBeUndefined();
    expect(trustedClientAddress("not-an-ip", 1)).toBeUndefined();
    expect(trustedClientAddress("2001:db8::1", 1)).toBe("2001:db8::1");
  });
});

describe("client HMAC", () => {
  it("is a stable 64-hex pseudonym for one address and day, and reveals no address", () => {
    const value = deriveClientHmac("203.0.113.9", key, day);

    expect(value).toMatch(/^[0-9a-f]{64}$/);
    expect(value).toBe(deriveClientHmac("203.0.113.9", key, day + 1000));
    expect(value).not.toContain("203");
  });

  it("differs by address, key, and UTC day", () => {
    const base = deriveClientHmac("203.0.113.9", key, day);

    expect(deriveClientHmac("203.0.113.10", key, day)).not.toBe(base);
    expect(deriveClientHmac("203.0.113.9", Buffer.alloc(32, 2), day)).not.toBe(base);
    expect(deriveClientHmac("203.0.113.9", key, day + 24 * 60 * 60 * 1000)).not.toBe(base);
  });

  it("is absent without an address or a key", () => {
    expect(deriveClientHmac(undefined, key, day)).toBeUndefined();
    expect(deriveClientHmac("203.0.113.9", undefined, day)).toBeUndefined();
  });
});
