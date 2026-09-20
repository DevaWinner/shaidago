import { execFileSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

const check = process.argv.includes("--check");
const generatedPath = fileURLToPath(new URL("../src/lib/api/generated/schema.ts", import.meta.url));
const clientPath = fileURLToPath(new URL("../src/lib/api/generated/client.ts", import.meta.url));
const generatedDirectory = fileURLToPath(new URL("../src/lib/api/generated/", import.meta.url));
const schemaPath = fileURLToPath(new URL("../../../contracts/openapi.json", import.meta.url));
const cliPath = fileURLToPath(
  new URL("../node_modules/openapi-typescript/bin/cli.js", import.meta.url)
);
const header = "// GENERATED FROM contracts/openapi.json. DO NOT EDIT BY HAND.\n\n";
const tempDirectory = await mkdtemp(`${tmpdir()}/shaidago-openapi-`);
const tempOutput = `${tempDirectory}/schema.ts`;

try {
  execFileSync(process.execPath, [cliPath, schemaPath, "--alphabetize", "--output", tempOutput], {
    stdio: "inherit"
  });
  const generated = header + (await readFile(tempOutput, "utf8"));
  const client = `${header}import createClient from "openapi-fetch";\n\nimport type { paths } from "./schema";\n\nexport function createGeneratedClient(baseUrl: string): ReturnType<typeof createClient<paths>> {\n  return createClient<paths>({ baseUrl });\n}\n`;

  if (check) {
    const committed = await readFile(generatedPath, "utf8").catch(() => "");
    const committedClient = await readFile(clientPath, "utf8").catch(() => "");
    if (committed !== generated || committedClient !== client) {
      throw new Error("Generated API types are stale. Run pnpm --dir apps/web api:generate.");
    }
  } else {
    await mkdir(generatedDirectory, { recursive: true });
    await writeFile(generatedPath, generated, "utf8");
    await writeFile(clientPath, client, "utf8");
  }
} finally {
  await rm(tempDirectory, { force: true, recursive: true });
}
