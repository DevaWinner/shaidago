import { defineConfig, devices } from "@playwright/test";

const port = 3101;
const baseURL = `http://127.0.0.1:${port}`;

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
  webServer: {
    command: `pnpm start -- --hostname 127.0.0.1 --port ${port}`,
    cwd: ".",
    url: baseURL,
    reuseExistingServer: !process.env["CI"],
    timeout: 120_000,
    stdout: "ignore",
    stderr: "pipe"
  }
});
