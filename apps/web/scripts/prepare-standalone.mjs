import { cp, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const assets = [
  {
    source: new URL("../.next/static", import.meta.url),
    destination: new URL("../.next/standalone/apps/web/.next/static", import.meta.url),
    required: true
  },
  {
    source: new URL("../public", import.meta.url),
    destination: new URL("../.next/standalone/apps/web/public", import.meta.url),
    required: false
  }
];

async function copyDirectoryWhenPresent(source, destination, required) {
  try {
    const sourceStats = await stat(source);

    if (!sourceStats.isDirectory()) {
      throw new Error(`Expected a directory at ${fileURLToPath(source)}.`);
    }
  } catch (error) {
    if (!required && isMissingDirectory(error)) {
      return;
    }

    throw error;
  }

  await cp(source, destination, { force: true, recursive: true });
}

function isMissingDirectory(error) {
  return typeof error === "object" && error !== null && "code" in error && error.code === "ENOENT";
}

await Promise.all(
  assets.map(({ source, destination, required }) =>
    copyDirectoryWhenPresent(source, destination, required)
  )
);
