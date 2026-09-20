import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineProject } from "vitest/config";

export default defineProject({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  },
  test: {
    name: "component",
    environment: "jsdom",
    include: ["tests/component/**/*.test.tsx"],
    setupFiles: ["./tests/setup.ts"],
    clearMocks: true,
    restoreMocks: true
  }
});
