import { fileURLToPath } from "node:url";

import { defineProject } from "vitest/config";

export default defineProject({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "server-only": fileURLToPath(new URL("./tests/stubs/server-only.ts", import.meta.url))
    }
  },
  test: {
    name: "unit",
    environment: "node",
    include: ["tests/unit/**/*.test.ts"],
    // next-intl imports `next/server` without an extension, which Node ESM cannot resolve.
    server: { deps: { inline: ["next-intl"] } },
    clearMocks: true,
    restoreMocks: true
  }
});
