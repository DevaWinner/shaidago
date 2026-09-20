import { z } from "zod";

/**
 * Outer-boundary shape checks for reviewer mutations. Enumerations mirror OpenAPI so an unknown
 * value is refused early, but which command is *allowed* from the current state stays a
 * FastAPI decision (`409`); the BFF never narrows or interprets a transition.
 */

const digest = z.string().regex(/^[0-9a-f]{64}$/);
const concept = z.string().min(1).max(80);

export const signInInput = z
  .object({ identifier: z.string().min(1).max(128), password: z.string().min(1).max(256) })
  .strict();

export const noteInput = z.object({ body: z.string().min(1).max(4500) }).strict();

export const reviewerQuestionInput = z.object({ question: z.string().min(1).max(600) }).strict();

export const transitionInput = z
  .object({
    command: z.enum([
      "request_information",
      "start_review",
      "close",
      "resume_review",
      "verify_for_public_update",
      "refer",
      "reopen",
      "record_follow_up"
    ]),
    expected_status: z.enum([
      "received",
      "needs_information",
      "under_review",
      "verified_for_public_update",
      "referred",
      "closed"
    ]),
    expected_version: z.number().int().min(1),
    internal_reason: z.string().max(1200).nullish(),
    reporter_message: z.string().max(400).nullish()
  })
  .strict();

const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);

export const draftInput = z
  .object({
    statement: z.string().min(1).max(2100),
    effective_on: isoDate,
    last_checked_on: isoDate.nullish(),
    verification_state: z.enum([
      "verified_official",
      "corroborated",
      "community_reviewed",
      "disputed",
      "outdated"
    ]),
    citations: z
      .array(
        z
          .object({
            source_version_id: z.uuid(),
            passage: z.string().min(1).max(1000),
            location_label: z.string().min(1).max(200)
          })
          .strict()
      )
      .min(1)
      .max(5)
  })
  .strict();

export const publishInput = z.object({ preview_digest: digest }).strict();

export const planInput = z.object({ concepts: z.array(concept).max(20).default([]) }).strict();

export const runCreateInput = z
  .object({ approved_digest: digest, concepts: z.array(concept).max(20).default([]) })
  .strict();

export const reviewInput = z
  .object({ command: z.enum(["approve_completion", "reject_run"]) })
  .strict();

export const discoveryAnswerInput = z
  .object({
    question_index: z.number().int().min(0).max(4),
    kind: z.enum(["answered", "skipped", "unsafe"]),
    answer: z.string().max(2100).nullish()
  })
  .strict();

export const decisionInput = z
  .object({
    command: z.enum(["attach", "reject", "defer", "reconsider"]),
    reason: z.string().max(400)
  })
  .strict();

export const idParam = z.uuid();

/**
 * Zod reports an omitted optional field as `undefined`; the generated request types use exact
 * optional properties. Removing undefined-valued keys cannot add or change a value.
 */
export function dropUndefined<T extends object>(
  value: T
): { [K in keyof T]: Exclude<T[K], undefined> } {
  return Object.fromEntries(Object.entries(value).filter(([, entry]) => entry !== undefined)) as {
    [K in keyof T]: Exclude<T[K], undefined>;
  };
}
