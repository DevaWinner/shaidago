import { z } from "zod";

import type { components } from "@/lib/api/generated/schema";

/**
 * Outer-boundary shape checks for browser input. They bound size and structure so a malformed
 * request never reaches the API; FastAPI still owns every domain rule. `.strict()` refuses
 * unknown fields rather than forwarding them.
 */

/** Same rule as the API path pattern `^[a-z0-9]+(-[a-z0-9]+)*$`, written without a nested quantifier. */
export function isProjectSlug(value: string): boolean {
  return (
    /^[a-z0-9-]{1,80}$/.test(value) &&
    !value.startsWith("-") &&
    !value.endsWith("-") &&
    !value.includes("--")
  );
}

const slug = z.string().refine(isProjectSlug, { message: "slug" });

export const questionInput = z.object({ slug, question: z.string().min(1).max(300) }).strict();

export const discoveryStartInput = z.object({ slug }).strict();

export const statusLookupInput = z.object({ code: z.string().min(1).max(256) }).strict();

export const credentialsInput = z
  .object({ handle: z.string().min(1).max(64), passphrase: z.string().min(1).max(200) })
  .strict();

export const followUpInput = z
  .object({
    question_id: z.uuid(),
    kind: z.enum(["answered", "skipped", "unsafe"]),
    answer: z.string().max(2500).optional(),
    code: z.string().min(1).max(256).optional(),
    handle: z.string().min(1).max(64).optional(),
    passphrase: z.string().min(1).max(200).optional()
  })
  .strict()
  .superRefine((value, context) => {
    const byCode = value.code !== undefined;
    const byHandle = value.handle !== undefined || value.passphrase !== undefined;

    // Exactly one credential form: a tracking code, or a handle together with its passphrase.
    if (
      byCode === byHandle ||
      (byHandle && (value.handle === undefined || value.passphrase === undefined))
    ) {
      context.addIssue({ code: "custom", path: ["code"], message: "credential" });
    }
  });

export function toAnswerRequest(
  input: z.infer<typeof followUpInput>
): components["schemas"]["AnswerRequest"] {
  return {
    question_id: input.question_id,
    kind: input.kind,
    ...(input.answer === undefined ? {} : { answer: input.answer }),
    ...(input.code === undefined ? {} : { code: input.code }),
    ...(input.handle === undefined ? {} : { handle: input.handle }),
    ...(input.passphrase === undefined ? {} : { passphrase: input.passphrase })
  };
}

export const runIdSchema = z.uuid();
export const sinceVersionSchema = z.coerce.number().int().min(0).max(1_000_000);
