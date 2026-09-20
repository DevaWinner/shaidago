/** Same rule as the API path pattern `^[a-z0-9]+(-[a-z0-9]+)*$`, written without a nested quantifier. */
export function isProjectSlug(value: string): boolean {
  return (
    /^[a-z0-9-]{1,80}$/.test(value) &&
    !value.startsWith("-") &&
    !value.endsWith("-") &&
    !value.includes("--")
  );
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isUuid(value: string): boolean {
  return UUID.test(value);
}
