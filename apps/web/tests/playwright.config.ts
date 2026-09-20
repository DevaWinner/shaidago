import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const port = 3100;
const baseURL = `http://127.0.0.1:${port}`;
const webRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig({
  testDir: "./e2e",
  forbidOnly: Boolean(process.env["CI"]),
  fullyParallel: false,
  reporter: process.env["CI"] ? "dot" : "list",
  timeout: 30_000,
  use: {
    baseURL,
    trace: "retain-on-failure",
    video: "off"
  },
  projects: [
    {
      name: "chromium",
      use: devices["Desktop Chrome"]
    },
    {
      name: "mobile-webkit",
      use: {
        ...devices["iPhone 13"],
        browserName: "webkit"
      }
    }
  ],
  webServer: {
    command: `HOSTNAME=127.0.0.1 PORT=${port} node .next/standalone/apps/web/server.js`,
    cwd: webRoot,
    url: baseURL,
    reuseExistingServer: !process.env["CI"],
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe"
  }
});
