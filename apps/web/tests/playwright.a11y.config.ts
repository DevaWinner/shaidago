import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const port = 3101;
const mockPort = port + 100;
const baseURL = `http://127.0.0.1:${port}`;
const webRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig({
  testDir: "./a11y",
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
  webServer: [
    {
      // A fictional stand-in for the public catalogue endpoints; see tests/support/mock-api.mjs.
      command: `MOCK_API_PORT=${mockPort} INTERNAL_WEB_CREDENTIAL_CURRENT=shaida-go-browser-test-credential-not-a-secret node tests/support/mock-api.mjs`,
      cwd: webRoot,
      url: `http://127.0.0.1:${mockPort}/health/live`,
      reuseExistingServer: !process.env["CI"],
      timeout: 30_000,
      stdout: "ignore",
      stderr: "pipe"
    },
    {
      command: `APP_ENV=test API_INTERNAL_URL=http://127.0.0.1:${mockPort} INTERNAL_WEB_CREDENTIAL_CURRENT=shaida-go-browser-test-credential-not-a-secret HOSTNAME=127.0.0.1 PORT=${port} pnpm run start:standalone`,
      cwd: webRoot,
      url: baseURL,
      reuseExistingServer: !process.env["CI"],
      timeout: 120_000,
      stdout: "ignore",
      stderr: "pipe"
    }
  ]
});
