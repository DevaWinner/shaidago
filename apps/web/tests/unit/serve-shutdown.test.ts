import { spawn } from "node:child_process";
import { copyFileSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it } from "vitest";

// `scripts/serve.mjs` is the container entry point. It is exercised against a stand-in `server.js`
// that answers slowly, so a request really is in flight when the signal arrives.
const directories: string[] = [];

afterEach(() => {
  while (directories.length > 0)
    rmSync(directories.pop() as string, { recursive: true, force: true });
});

function launch(port: number, grace = "5000") {
  const directory = mkdtempSync(join(tmpdir(), "sg-serve-"));

  directories.push(directory);
  copyFileSync(
    join(import.meta.dirname, "..", "..", "scripts", "serve.mjs"),
    join(directory, "serve.mjs")
  );
  writeFileSync(
    join(directory, "server.js"),
    `const http = require("node:http");
     http.createServer((request, response) => {
       setTimeout(() => response.end("finished"), request.url === "/slow" ? 1500 : 0);
     }).listen(${port}, "127.0.0.1", () => console.log("ready"));`
  );
  const child = spawn(process.execPath, [join(directory, "serve.mjs")], {
    env: { ...process.env, SHUTDOWN_GRACE_MS: grace },
    stdio: ["ignore", "pipe", "pipe"]
  });
  const output: string[] = [];

  child.stdout.on("data", (chunk: Buffer) => output.push(String(chunk)));

  return { child, output };
}

const ready = async (port: number): Promise<void> => {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      await fetch(`http://127.0.0.1:${port}/fast`);

      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  throw new Error("stand-in server did not start");
};

describe("container entry point", () => {
  it("lets an in-flight request finish, refuses new ones while draining, and exits 0", async () => {
    const port = 39100 + Math.floor(Math.random() * 500);
    const { child, output } = launch(port);
    const exited = new Promise<number | null>((resolve) =>
      child.on("exit", (code) => resolve(code))
    );

    await ready(port);
    const inFlight = fetch(`http://127.0.0.1:${port}/slow`).then((response) => response.text());

    await new Promise((resolve) => setTimeout(resolve, 300));
    const started = Date.now();

    child.kill("SIGTERM");
    await new Promise((resolve) => setTimeout(resolve, 150));
    await expect(fetch(`http://127.0.0.1:${port}/fast`)).rejects.toThrow();
    expect(await inFlight).toBe("finished");
    expect(await exited).toBe(0);
    expect(Date.now() - started).toBeLessThan(4000);
    expect(output.join("")).toContain("SIGTERM received: draining");
  });

  it("gives up after the grace period so a stuck request cannot hold a deploy, still exiting 0", async () => {
    const port = 39700 + Math.floor(Math.random() * 200);
    const { child } = launch(port, "400");
    const exited = new Promise<number | null>((resolve) =>
      child.on("exit", (code) => resolve(code))
    );

    await ready(port);
    void fetch(`http://127.0.0.1:${port}/slow`).catch(() => undefined);
    await new Promise((resolve) => setTimeout(resolve, 200));
    const started = Date.now();

    child.kill("SIGTERM");
    expect(await exited).toBe(0);
    expect(Date.now() - started).toBeLessThan(1400);
  });
});
