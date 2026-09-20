import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST as lookupStatus } from "../../app/api/tracking/lookup/route";
import { POST as submitReport } from "../../app/api/reports/route";
import { POST as createNote } from "../../app/api/reviewer/reports/[reportId]/notes/route";
import { POST as signIn } from "../../app/api/reviewer/session/route";
import { GET as downloadEvidence } from "../../app/api/reviewer/reports/[reportId]/evidence/[evidenceId]/route";

const root = join(import.meta.dirname, "..", "..");
const apiRoot = join(root, "app", "api");

function files(directory: string, filter: (name: string) => boolean): string[] {
  return readdirSync(directory).flatMap((name) => {
    const path = join(directory, name);

    return statSync(path).isDirectory() ? files(path, filter) : filter(name) ? [path] : [];
  });
}

function declaredMethods(file: string): string[] {
  return [
    ...readFileSync(file, "utf8").matchAll(
      /^export (?:async )?function (GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b/gm
    )
  ].map((match) => match[1] ?? "");
}

describe("operation map coverage", () => {
  const map = readFileSync(join(root, "..", "..", "docs", "FRONTEND_BFF_OPERATION_MAP.md"), "utf8");
  const mapped = new Set(
    [...map.matchAll(/`(GET|POST|DELETE) (app\/api\/[^`]+?\/route\.ts)`/g)].map(
      (match) => `${match[1]} ${match[2]}`
    )
  );
  const implemented = new Set(
    files(apiRoot, (name) => name === "route.ts").flatMap((file) =>
      declaredMethods(file).map(
        (method) => `${method} ${join("app", "api", relative(apiRoot, file)).split(sep).join("/")}`
      )
    )
  );

  it("implements every browser route the operation map names, with the exact method", () => {
    expect([...mapped].filter((entry) => !implemented.has(entry)).toSorted()).toEqual([]);
  });

  it("has no route the operation map does not name, and no generic proxy", () => {
    expect([...implemented].filter((entry) => !mapped.has(entry)).toSorted()).toEqual([]);
    expect(
      files(apiRoot, () => true).filter((file) => /\[\.\.\.|proxy/i.test(relative(apiRoot, file)))
    ).toEqual([]);
    expect(mapped.size).toBeGreaterThanOrEqual(26);
  });
});

describe("no logging from the BFF", () => {
  it("never calls a console or logger from handlers or BFF libraries", () => {
    const sources = [
      ...files(apiRoot, (name) => name === "route.ts"),
      ...files(join(root, "src", "lib", "bff"), (name) => name.endsWith(".ts")),
      join(root, "src", "lib", "api", "server.ts")
    ];

    for (const file of sources) {
      expect(readFileSync(file, "utf8"), file).not.toMatch(
        /\bconsole\.|\blogger\b|process\.std(?:out|err)/
      );
    }
  });
});

describe("sensitive-value log redaction at runtime", () => {
  const canary = "SG-CANARY-TRACKING-CODE-VALUE";
  const secretHost = "10.9.8.7";
  const origin = "http://localhost:3000";
  const outputs: string[] = [];

  beforeEach(() => {
    vi.stubEnv("APP_ENV", "test");
    vi.stubEnv("API_INTERNAL_URL", "http://api.internal-test.invalid");
    vi.stubEnv("INTERNAL_WEB_CREDENTIAL_CURRENT", "shaida-go-unit-test-credential-not-a-secret");
    vi.stubEnv("NEXT_PUBLIC_APP_ORIGIN", undefined);
    outputs.length = 0;

    for (const method of ["log", "info", "warn", "error", "debug", "trace"] as const) {
      vi.spyOn(console, method).mockImplementation((...args: unknown[]) => {
        outputs.push(args.map(String).join(" "));
      });
    }
    vi.spyOn(process.stdout, "write").mockImplementation((chunk: unknown) => {
      outputs.push(String(chunk));
      return true;
    });
    vi.spyOn(process.stderr, "write").mockImplementation((chunk: unknown) => {
      outputs.push(String(chunk));
      return true;
    });
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("emits nothing while failing on private values, secrets, and internal hosts", async () => {
    const backend = vi.spyOn(globalThis, "fetch");
    const post = (path: string, body: unknown, headers: Record<string, string> = {}) =>
      new Request(`${origin}${path}`, {
        method: "POST",
        headers: { Origin: origin, "Content-Type": "application/json", ...headers },
        body: JSON.stringify(body)
      });

    backend.mockRejectedValue(new TypeError(`connect ECONNREFUSED ${secretHost}:8000 ${canary}`));
    await lookupStatus(post("/api/tracking/lookup", { code: canary }));
    await signIn(post("/api/reviewer/session", { identifier: canary, password: canary }));
    await createNote(
      post(
        "/api/reviewer/reports/0198f1a2-7b3c-4d4e-8f5a-123456789a01/notes",
        { body: canary },
        {
          Cookie: `sg_session=session-token-${canary}; sg_csrf=csrf-token-${canary}0000`
        }
      ),
      { params: Promise.resolve({ reportId: "0198f1a2-7b3c-4d4e-8f5a-123456789a01" }) }
    );
    await downloadEvidence(
      new Request(`${origin}/x`, { headers: { Cookie: `sg_session=session-token-${canary}` } }),
      {
        params: Promise.resolve({
          reportId: "0198f1a2-7b3c-4d4e-8f5a-123456789a01",
          evidenceId: "0198f1a2-7b3c-4d4e-8f5a-123456789a02"
        })
      }
    );
    await submitReport(
      new Request(`${origin}/api/reports`, {
        method: "POST",
        headers: {
          Origin: origin,
          "Content-Type": "multipart/form-data; boundary=x",
          "Idempotency-Key": "0198f1a2-7b3c-4d4e-8f5a-123456789abc"
        },
        body: `--x\r\n${canary}\r\n--x--`
      })
    );
    vi.stubEnv("API_INTERNAL_URL", "");
    await lookupStatus(post("/api/tracking/lookup", { code: canary }));

    expect(backend).toHaveBeenCalled();
    expect(outputs).toEqual([]);
  });

  it("never returns a canary or internal host in any failure response", async () => {
    const backend = vi.spyOn(globalThis, "fetch");
    backend.mockRejectedValue(new TypeError(`connect ECONNREFUSED ${secretHost}:8000 ${canary}`));

    const response = await lookupStatus(
      new Request(`${origin}/api/tracking/lookup`, {
        method: "POST",
        headers: { Origin: origin, "Content-Type": "application/json" },
        body: JSON.stringify({ code: canary })
      })
    );
    const text = `${await response.text()} ${[...response.headers].join(" ")}`;

    expect(text).not.toContain(canary);
    expect(text).not.toContain(secretHost);
    expect(text).not.toContain("api.internal-test.invalid");
    expect(text).not.toContain("shaida-go-unit-test-credential");
  });
});
