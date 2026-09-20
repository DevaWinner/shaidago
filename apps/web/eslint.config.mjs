import { defineConfig, globalIgnores } from "eslint/config";
import nextTypescript from "eslint-config-next/typescript";
import nextVitals from "eslint-config-next/core-web-vitals";
import prettier from "eslint-config-prettier";
import security from "eslint-plugin-security";

export default defineConfig([
  ...nextVitals,
  ...nextTypescript,
  {
    files: ["**/*.{js,mjs,cjs,ts,tsx}"],
    plugins: {
      security
    },
    rules: {
      "import/no-duplicates": "error",
      "import/no-mutable-exports": "error",
      "jsx-a11y/no-autofocus": "error",
      "jsx-a11y/no-static-element-interactions": "error",
      "security/detect-unsafe-regex": "error"
    }
  },
  prettier,
  globalIgnores([
    ".next/**",
    "coverage/**",
    "node_modules/**",
    "playwright-report/**",
    "test-results/**",
    "next-env.d.ts"
  ])
]);
