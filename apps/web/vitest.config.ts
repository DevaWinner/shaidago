import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    projects: ["./vitest.unit.config.ts", "./vitest.component.config.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      reportsDirectory: "coverage",
      thresholds: {
        branches: 80,
        functions: 80,
        lines: 80,
        statements: 80
      }
    }
  }
});
