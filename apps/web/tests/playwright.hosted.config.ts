import { defineConfig, devices } from "@playwright/test";

/**
 * The hosted smoke matrix (FE-162). It runs against a deployed origin, never starts a server, and
 * uses only fictional input. Set HOSTED_ORIGIN, and (optionally) HOSTED_REVIEWER and
 * HOSTED_REVIEWER_PASSWORD to include the reviewer steps. Traces, screenshots, and video are off,
 * so nothing from a hosted run is retained.
 *   HOSTED_ORIGIN=https://... pnpm --dir apps/web exec playwright test --config tests/playwright.hosted.config.ts
 */
const origin = process.env["HOSTED_ORIGIN"];

if (origin === undefined || !origin.startsWith("https://")) {
  throw new Error("Set HOSTED_ORIGIN to the deployed https origin.");
}

export default defineConfig({
  testDir: "./hosted",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  timeout: 60_000,
  use: { baseURL: origin, trace: "off", video: "off", screenshot: "off" },
  projects: [
    { name: "chromium-desktop", use: devices["Desktop Chrome"] },
    { name: "mobile-webkit", use: { ...devices["iPhone 13"], browserName: "webkit" } }
  ]
});
