import { z } from "zod";

const publicEnvironmentNames = ["NEXT_PUBLIC_APP_ORIGIN"] as const;

type EnvironmentValues = Readonly<Record<string, string | undefined>>;

const unsafePublicNamePattern =
  /(api|credential|database|key|password|private|redis|secret|storage|token)/i;

const publicEnvironmentSchema = z
  .object({
    appOrigin: z.url().optional()
  })
  .readonly();

export type PublicEnvironment = z.infer<typeof publicEnvironmentSchema>;

export class PublicEnvironmentError extends Error {
  public readonly code = "invalid_public_environment";

  public constructor(public readonly names: readonly string[]) {
    super(`Invalid public environment configuration: ${names.join(", ")}.`);
    this.name = "PublicEnvironmentError";
  }
}

function isAllowedPublicEnvironmentName(name: string): boolean {
  return publicEnvironmentNames.some((allowedName) => allowedName === name);
}

function publicEnvironmentNamesFrom(environment: EnvironmentValues): readonly string[] {
  return Object.keys(environment).filter((name) => name.startsWith("NEXT_PUBLIC_"));
}

/**
 * Returns the only configuration a future client module may read. Names that look secret-like are
 * refused even when they carry the public prefix, preventing accidental browser exposure.
 */
export function loadPublicEnvironment(
  environment: EnvironmentValues = process.env
): PublicEnvironment {
  const invalidNames = publicEnvironmentNamesFrom(environment).filter(
    (name) => !isAllowedPublicEnvironmentName(name) || unsafePublicNamePattern.test(name)
  );

  if (invalidNames.length > 0) {
    throw new PublicEnvironmentError(invalidNames.toSorted());
  }

  const parsedEnvironment = publicEnvironmentSchema.safeParse({
    appOrigin: environment["NEXT_PUBLIC_APP_ORIGIN"]
  });

  if (!parsedEnvironment.success) {
    throw new PublicEnvironmentError(["NEXT_PUBLIC_APP_ORIGIN"]);
  }

  return parsedEnvironment.data;
}
