/**
 * The container's entry point: it starts the framework's standalone server and adds a graceful
 * shutdown. On SIGTERM it stops accepting new connections, lets in-flight requests finish, closes
 * idle keep-alive connections, and exits 0, or exits 0 after SHUTDOWN_GRACE_MS (default 20 s, kept
 * under the platform's 25 s drain) so a stuck request cannot hold a deploy. Without this the
 * server exits at once and cuts a report upload or a download in half.
 */
import http from "node:http";
import { fileURLToPath } from "node:url";

const servers = [];
const createServer = http.createServer;

http.createServer = function patched(...args) {
  const server = createServer.apply(this, args);

  servers.push(server);

  return server;
};

// The framework's own handler exits immediately; this file takes over the signal instead.
process.env["NEXT_MANUAL_SIG_HANDLE"] = "true";

const grace = Number(process.env["SHUTDOWN_GRACE_MS"] ?? 20_000);
let stopping = false;

function shutdown(signal) {
  if (stopping) return;
  stopping = true;
  process.stdout.write(`${signal} received: draining\n`);
  const timer = setTimeout(() => {
    process.stdout.write("grace period over: exiting\n");
    process.exit(0);
  }, grace);

  timer.unref();
  // A connection that finishes its request becomes idle and would otherwise sit out its keep-alive
  // timeout; close such connections as soon as they appear.
  const sweep = setInterval(() => {
    for (const server of servers) server.closeIdleConnections?.();
  }, 50);

  sweep.unref();
  Promise.all(
    servers.map(
      (server) =>
        new Promise((resolve) => {
          server.close(() => resolve(undefined));
          server.closeIdleConnections?.();
        })
    )
  ).then(() => process.exit(0));
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));

await import(fileURLToPath(new URL("./server.js", import.meta.url)));
