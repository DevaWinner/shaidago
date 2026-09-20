import "server-only";

import { z } from "zod";

const placeholderPattern = /change-me/i;

type EnvironmentValues = Readonly<Record<string, string | undefined>>;

const fieldToEnvironmentName = {
  appEnvironment: "APP_ENV",
  apiInternalUrl: "API_INTERNAL_URL",
  internalWebCredential: "INTERNAL_WEB_CREDENTIAL_CURRENT"
} as const;

const serverEnvironmentSchema = z
  .object({
    appEnvironment: z.enum(["development", "test", "staging", "production"]),
    apiInternalUrl: z.url().refine(
      (value) => {
        const url = new URL(value);

        return url.protocol === "http:" || url.protocol === "https:";
      },
      { message: "must use http or https" }
    ),
    internalWebCredential: z.string().trim().min(32)
  })
  .readonly();

export type ServerEnvironment = z.infer<typeof serverEnvironmentSchema>;

export class ServerEnvironmentError extends Error {
  public readonly code = "invalid_server_environment";

  public constructor(public readonly names: readonly string[]) {
    super(`Invalid server environment configuration: ${names.join(", ")}.`);
    this.name = "ServerEnvironmentError";
  }
}

function invalidServerEnvironmentNames(
  environment: EnvironmentValues,
  parsedEnvironment: z.ZodSafeParseResult<ServerEnvironment>
): readonly string[] {
  const names = new Set<string>();

  if (!parsedEnvironment.success) {
    for (const issue of parsedEnvironment.error.issues) {
      const [field] = issue.path;

      if (typeof field === "string" && field in fieldToEnvironmentName) {
        names.add(fieldToEnvironmentName[field as keyof typeof fieldToEnvironmentName]);
      }
    }
  }

  if (environment["APP_ENV"] === "staging" || environment["APP_ENV"] === "production") {
    if (placeholderPattern.test(environment["INTERNAL_WEB_CREDENTIAL_CURRENT"] ?? "")) {
      names.add("INTERNAL_WEB_CREDENTIAL_CURRENT");
    }
  }

  return [...names].toSorted();
}

/**
 * This module is server-only and intentionally reads process environment at call time. Next's
 * build phase must not need a private Railway URL or BFF credential; runtime startup validates both.
 */
export function loadServerEnvironment(
  environment: EnvironmentValues = process.env
): ServerEnvironment {
  const parsedEnvironment = serverEnvironmentSchema.safeParse({
    appEnvironment: environment["APP_ENV"],
    apiInternalUrl: environment["API_INTERNAL_URL"],
    internalWebCredential: environment["INTERNAL_WEB_CREDENTIAL_CURRENT"]
  });
  const invalidNames = invalidServerEnvironmentNames(environment, parsedEnvironment);

  if (invalidNames.length > 0 || !parsedEnvironment.success) {
    throw new ServerEnvironmentError(invalidNames);
  }

  return parsedEnvironment.data;
}
