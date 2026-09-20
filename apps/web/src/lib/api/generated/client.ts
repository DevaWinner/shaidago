// GENERATED FROM contracts/openapi.json. DO NOT EDIT BY HAND.

import createClient from "openapi-fetch";

import type { paths } from "./schema";

export function createGeneratedClient(baseUrl: string): ReturnType<typeof createClient<paths>> {
  return createClient<paths>({ baseUrl });
}
