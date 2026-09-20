import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const clientDirectory = path.join(import.meta.dirname, "..", ".next", "static");
const sensitiveEnvironmentNames = [
  "API_INTERNAL_URL",
  "INTERNAL_WEB_CREDENTIAL_CURRENT",
  "INTERNAL_WEB_CREDENTIAL_PREVIOUS",
  "GROQ_API_KEY",
  "SEARCH_API_KEY",
  "EMBEDDING_API_KEY",
  "OBJECT_STORE_ACCESS_KEY_ID",
  "OBJECT_STORE_SECRET_ACCESS_KEY"
];

async function collectJavaScriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const filePath = path.join(directory, entry.name);

      if (entry.isDirectory()) {
        return collectJavaScriptFiles(filePath);
      }

      return entry.isFile() && filePath.endsWith(".js") ? [filePath] : [];
    })
  );

  return files.flat();
}

function getRequiredCanaries() {
  return sensitiveEnvironmentNames.map((name) => {
    const value = process.env[name];

    if (!value) {
      throw new Error(`Missing boundary-test environment variable: ${name}.`);
    }

    return { name, value };
  });
}

async function main() {
  const canaries = getRequiredCanaries();
  const files = await collectJavaScriptFiles(clientDirectory);
  const forbiddenValues = [
    ...sensitiveEnvironmentNames,
    ...canaries.map((canary) => canary.value),
    "server-only",
    "src/lib/config/server",
    // BFF-only wire details: none of these has a reason to exist in browser code.
    "X-Shaidago-Session",
    "X-Shaidago-Csrf",
    "X-Shaidago-Client-Hmac",
    "Bearer web.",
    "__Host-sg_session",
    "sg_csrf",
    "/v1/reviewer",
    "/v1/reports",
    "src/lib/bff",
    "src/lib/api/server"
  ];
  const leakedNames = new Set();

  for (const filePath of files) {
    const source = await readFile(filePath, "utf8");

    for (const forbiddenValue of forbiddenValues) {
      if (source.includes(forbiddenValue)) {
        const canary = canaries.find((candidate) => candidate.value === forbiddenValue);
        leakedNames.add(canary?.name ?? forbiddenValue);
      }
    }
  }

  if (leakedNames.size > 0) {
    throw new Error(`Forbidden client-bundle content: ${[...leakedNames].toSorted().join(", ")}.`);
  }

  process.stdout.write(`Client boundary verified across ${files.length} JavaScript chunks.\n`);
}

await main();
