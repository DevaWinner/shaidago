/**
 * Makes a pasted tracking code easier to accept without deciding whether it is valid: the service
 * does that, and answers the same way for every code it does not recognise. Only whitespace, zero-width
 * characters, and look-alike dashes are changed; letters and digits are never altered, so a code is
 * never "fixed" into a different one.
 */
export const CODE_MAX = 256;

export function normaliseCode(input: string): string {
  return input
    .normalize("NFKC")
    .replace(/[​-‍⁠﻿]/g, "")
    .replace(/[‐-―−]/g, "-")
    .replace(/\s+/g, "");
}
