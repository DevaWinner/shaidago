import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { LOCALES, checkCatalogues, pendingKeys } from "./messages-parity.mjs";

const directory = path.join(import.meta.dirname, "..", "messages");
const read = async (name) =>
  JSON.parse(await readFile(path.join(directory, `${name}.json`), "utf8"));

const catalogues = Object.fromEntries(
  await Promise.all(LOCALES.map(async (locale) => [locale, await read(locale)]))
);
const status = await read("status");
const errors = checkCatalogues({ catalogues, status });

if (errors.length > 0) {
  process.stderr.write(
    `Message catalogue check failed:\n${errors.map((error) => `- ${error}`).join("\n")}\n`
  );
  process.exit(1);
}

process.stdout.write(`Message catalogues consistent across ${LOCALES.join(", ")}.\n`);

for (const [locale, keys] of Object.entries(pendingKeys({ catalogues }))) {
  if (keys.length > 0) {
    process.stdout.write(
      `  ${locale}: ${keys.length} key(s) waiting for translation${status.pendingKeysAllowed ? " (allowed during the build)" : ""}\n`
    );
  }
}
