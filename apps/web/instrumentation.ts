type EnvironmentValues = Readonly<Record<string, string | undefined>>;

export async function validateRuntimeEnvironment(
  environment: EnvironmentValues = process.env
): Promise<void> {
  if (environment["NEXT_RUNTIME"] !== "nodejs") {
    return;
  }

  const { loadServerEnvironment } = await import("./src/lib/config/server");

  loadServerEnvironment(environment);
}

export async function register(): Promise<void> {
  await validateRuntimeEnvironment();
}
