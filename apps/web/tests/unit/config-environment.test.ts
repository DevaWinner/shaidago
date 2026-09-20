import { describe, expect, it } from "vitest";

import { PublicEnvironmentError, loadPublicEnvironment } from "@/lib/config/public";
import { ServerEnvironmentError, loadServerEnvironment } from "@/lib/config/server";
import { validateRuntimeEnvironment } from "../../instrumentation";

const validServerEnvironment = {
  APP_ENV: "test",
  API_INTERNAL_URL: "http://api.internal-test.invalid",
  INTERNAL_WEB_CREDENTIAL_CURRENT: "shaida-go-unit-test-credential-not-a-secret"
} as const;

describe("server environment", () => {
  it("fails closed when the Next Node runtime starts without private settings", async () => {
    await expect(validateRuntimeEnvironment({ NEXT_RUNTIME: "nodejs" })).rejects.toThrowError(
      ServerEnvironmentError
    );
  });

  it("accepts valid private settings at Next Node runtime startup", async () => {
    await expect(
      validateRuntimeEnvironment({
        NEXT_RUNTIME: "nodejs",
        ...validServerEnvironment
      })
    ).resolves.toBeUndefined();
  });

  it("validates private runtime settings without changing their values", () => {
    expect(loadServerEnvironment(validServerEnvironment)).toEqual({
      appEnvironment: "test",
      apiInternalUrl: "http://api.internal-test.invalid",
      internalWebCredential: "shaida-go-unit-test-credential-not-a-secret"
    });
  });

  it("reports variable names but never private values", () => {
    const secretValue = "private-value";

    expect(() =>
      loadServerEnvironment({
        ...validServerEnvironment,
        INTERNAL_WEB_CREDENTIAL_CURRENT: secretValue
      })
    ).toThrowError(ServerEnvironmentError);

    try {
      loadServerEnvironment({
        ...validServerEnvironment,
        INTERNAL_WEB_CREDENTIAL_CURRENT: secretValue
      });
    } catch (error: unknown) {
      expect(error).toBeInstanceOf(ServerEnvironmentError);
      expect(String(error)).toContain("INTERNAL_WEB_CREDENTIAL_CURRENT");
      expect(String(error)).not.toContain(secretValue);
    }
  });

  it("rejects a production placeholder credential", () => {
    expect(() =>
      loadServerEnvironment({
        ...validServerEnvironment,
        APP_ENV: "production",
        INTERNAL_WEB_CREDENTIAL_CURRENT: "change-me-web-credential-with-enough-characters"
      })
    ).toThrowError(ServerEnvironmentError);
  });
});

describe("public environment", () => {
  it("returns only the explicit safe browser setting", () => {
    expect(
      loadPublicEnvironment({
        NEXT_PUBLIC_APP_ORIGIN: "https://shaidago.example"
      })
    ).toEqual({ appOrigin: "https://shaidago.example" });
  });

  it("rejects unexpected or secret-like browser variables", () => {
    expect(() =>
      loadPublicEnvironment({
        NEXT_PUBLIC_API_KEY: "must-not-be-public"
      })
    ).toThrowError(PublicEnvironmentError);
  });

  it("does not include an invalid public value in its error", () => {
    const invalidValue = "not-a-valid-origin/private-value";

    expect(() =>
      loadPublicEnvironment({
        NEXT_PUBLIC_APP_ORIGIN: invalidValue
      })
    ).toThrowError(PublicEnvironmentError);

    try {
      loadPublicEnvironment({
        NEXT_PUBLIC_APP_ORIGIN: invalidValue
      });
    } catch (error: unknown) {
      expect(error).toBeInstanceOf(PublicEnvironmentError);
      expect(String(error)).not.toContain(invalidValue);
    }
  });
});
