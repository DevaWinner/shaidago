import type en from "../../../messages/en.json";

/**
 * Turns a stable problem code into reviewed copy. Only the `code` (and field paths with rule codes)
 * ever choose text; a backend `title` or `detail` is never displayed, so an unexpected message, a
 * hostname, or a submitted value cannot reach a resident. An unknown code gets a generic message
 * plus the support reference, never a guess at what went wrong.
 */

type ProblemsCopy = (typeof en)["problems"];
export type ProblemMessageKey = keyof ProblemsCopy["codes"];
export type RuleMessageKey = keyof ProblemsCopy["rules"];

/** Every code the API contract or the BFF can return, mapped to one message. */
export const PROBLEM_CODE_KEYS = {
  bad_request: "badRequest",
  invalid_json: "badRequest",
  idempotency_key_invalid: "badRequest",
  method_not_allowed: "badRequest",
  unauthenticated: "unauthenticated",
  forbidden: "forbidden",
  not_found: "notFound",
  tracking_code_not_recognised: "codeNotRecognised",
  invalid_credentials: "invalidCredentials",
  invalid_reporter_credentials: "invalidCredentials",
  rate_limited: "rateLimited",
  conflict: "conflict",
  report_version_conflict: "conflict",
  preview_stale: "conflict",
  idempotency_conflict: "idempotencyConflict",
  report_status_transition_not_allowed: "notAllowedNow",
  public_update_not_draft: "notAllowedNow",
  public_update_report_not_verified: "notAllowedNow",
  payload_too_large: "tooLarge",
  unsupported_media_type: "unsupportedType",
  validation_failed: "validationFailed",
  markup_not_allowed: "markupNotAllowed",
  publication_incomplete: "publicationIncomplete",
  invalid_cursor: "invalidCursor",
  query_changed: "queryChanged",
  csrf_invalid: "notVerified",
  origin_forbidden: "notVerified",
  upstream_timeout: "timeout",
  dependency_unavailable: "unavailable",
  request_aborted: "aborted",
  network_unavailable: "network",
  internal_error: "internal"
} as const satisfies Readonly<Record<string, ProblemMessageKey>>;

export type KnownProblemCode = keyof typeof PROBLEM_CODE_KEYS;

/** Codes after which a mutation may or may not have been applied, so the retry hint is shown. */
const COMPLETION_UNKNOWN: ReadonlySet<string> = new Set([
  "upstream_timeout",
  "dependency_unavailable",
  "network_unavailable",
  "request_aborted",
  "internal_error"
]);

/** Validation rule codes from the API (pydantic) and the BFF (zod), grouped by what the user should do. */
const RULE_KEYS: Readonly<Record<string, RuleMessageKey>> = {
  missing: "required",
  too_small: "tooShort",
  string_too_short: "tooShort",
  greater_than_equal: "tooShort",
  greater_than: "tooShort",
  too_big: "tooLong",
  string_too_long: "tooLong",
  less_than_equal: "tooLong",
  less_than: "tooLong",
  invalid_type: "invalidFormat",
  invalid_format: "invalidFormat",
  invalid_value: "invalidFormat",
  string_pattern_mismatch: "invalidFormat",
  string_type: "invalidFormat",
  uuid_parsing: "invalidFormat",
  date_parsing: "invalidFormat",
  int_parsing: "invalidFormat",
  literal_error: "invalidFormat",
  enum: "invalidFormat",
  value_error: "invalidFormat",
  unrecognized_keys: "notAccepted",
  extra_forbidden: "notAccepted",
  markup_not_allowed: "markup"
};

export type SafeProblem = Readonly<{
  code: string;
  status: number | undefined;
  requestId: string | undefined;
  retryAfterSeconds: number | undefined;
  fieldErrors: readonly { readonly field: string; readonly code: string }[];
}>;

export type FormatMessage = (
  template: string,
  values: Readonly<Record<string, string | number>>
) => string;

export type ProblemView = Readonly<{
  /** The reviewed sentence for this problem. */
  message: string;
  /** True when the code was not recognised: the generic message is shown with the reference. */
  isGeneric: boolean;
  /** "Try again in 12 seconds." when the API said how long to wait. */
  retryHint: string | undefined;
  /** Shown after a timeout or network loss on a mutation, when it may have been applied. */
  mayHaveCompletedHint: string | undefined;
  /** "Support reference: <id>" (already localised), for generic and internal problems. */
  referenceLine: string | undefined;
  fieldErrors: readonly { readonly field: string; readonly message: string }[];
}>;

function isKnown(code: string): code is KnownProblemCode {
  return Object.hasOwn(PROBLEM_CODE_KEYS, code);
}

export function ruleMessage(rule: string, copy: ProblemsCopy): string {
  return copy.rules[Object.hasOwn(RULE_KEYS, rule) ? (RULE_KEYS[rule] ?? "invalid") : "invalid"];
}

export function describeProblem(
  problem: SafeProblem,
  copy: ProblemsCopy,
  format: FormatMessage,
  options: { readonly mutation?: boolean } = {}
): ProblemView {
  const known = isKnown(problem.code);
  const key: ProblemMessageKey = known ? PROBLEM_CODE_KEYS[problem.code] : "unknown";
  const needsReference = !known || key === "internal";

  return {
    message: copy.codes[key],
    isGeneric: !known,
    retryHint:
      problem.retryAfterSeconds === undefined
        ? undefined
        : format(copy.retryAfter, { seconds: problem.retryAfterSeconds }),
    mayHaveCompletedHint:
      options.mutation === true && COMPLETION_UNKNOWN.has(problem.code)
        ? copy.mayHaveCompleted
        : undefined,
    referenceLine:
      needsReference && problem.requestId !== undefined
        ? format(copy.reference, { reference: problem.requestId })
        : undefined,
    fieldErrors: problem.fieldErrors.map(({ field, code }) => ({
      field,
      message: ruleMessage(code, copy)
    }))
  };
}

/**
 * Maps API or BFF field paths (`body.description`, `description`, `query.limit`) to the form's own
 * control IDs. A path with no control is returned in `unmapped` so it is summarised, not lost.
 */
export function mapFieldErrors(
  errors: ProblemView["fieldErrors"],
  controlIds: Readonly<Record<string, string>>
): {
  mapped: readonly { controlId: string; message: string }[];
  unmapped: readonly string[];
} {
  const mapped: { controlId: string; message: string }[] = [];
  const unmapped: string[] = [];

  for (const { field, message } of errors) {
    const name = field.replace(/^(?:body|query|path)\./, "");
    const controlId = Object.hasOwn(controlIds, name) ? controlIds[name] : undefined;

    if (controlId === undefined) {
      unmapped.push(message);
    } else if (!mapped.some((entry) => entry.controlId === controlId)) {
      // One message per control: the first reported rule is the one to fix first.
      mapped.push({ controlId, message });
    }
  }

  return { mapped, unmapped };
}

/** Re-fills a form after a failed submit with everything except secrets, which are never restored. */
export function preservedValues<T extends Readonly<Record<string, unknown>>>(
  values: T,
  secretFields: readonly string[]
): Partial<T> {
  return Object.fromEntries(
    Object.entries(values).filter(
      ([name, value]) =>
        !secretFields.includes(name) && !(typeof File !== "undefined" && value instanceof File)
    )
  ) as Partial<T>;
}
