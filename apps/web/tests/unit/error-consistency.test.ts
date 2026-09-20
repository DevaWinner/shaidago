import { describe, expect, it } from "vitest";

import {
  describeProblem,
  PROBLEM_CODE_KEYS,
  type SafeProblem
} from "@/lib/problems/problem-messages";
import en from "../../messages/en.json";

const problem = (code: string, over: Partial<SafeProblem> = {}): SafeProblem => ({
  code,
  status: undefined,
  requestId: undefined,
  retryAfterSeconds: undefined,
  fieldErrors: [],
  ...over
});
const lite = (template: string, values: Record<string, string | number>) =>
  Object.entries(values).reduce(
    (text, [name, value]) => text.split(`{${name}}`).join(String(value)),
    template
  );
const say = (code: string, options: { mutation?: boolean } = {}) =>
  describeProblem(
    problem(code, { requestId: "0198f1a2-7b3c-4d4e-8f5a-123456789abc" }),
    en.problems,
    lite,
    options
  );

describe("errors are not collapsed into one generic state", () => {
  const classes = {
    "expired or missing sign-in": "unauthenticated",
    "not permitted": "forbidden",
    "not found": "not_found",
    "wrong credentials": "invalid_credentials",
    "too many requests": "rate_limited",
    "changed underneath the user": "report_version_conflict",
    "not allowed in this state": "report_status_transition_not_allowed",
    validation: "validation_failed",
    "markup refused": "markup_not_allowed",
    "cannot be verified (origin or CSRF)": "csrf_invalid",
    "dependency down": "dependency_unavailable",
    timeout: "upstream_timeout",
    "offline or unreachable": "network_unavailable",
    internal: "internal_error"
  } as const;

  it("gives each named class its own sentence, so a reader is told which thing happened", () => {
    const messages = Object.entries(classes).map(
      ([label, code]) => [label, say(code).message] as const
    );
    const seen = new Map<string, string>();

    for (const [label, message] of messages) {
      // The three "could not be verified" codes share one deliberate sentence; nothing else may repeat.
      const duplicate = seen.get(message);

      expect(
        duplicate === undefined || duplicate === label,
        `${label} repeats the sentence for ${duplicate}`
      ).toBe(true);
      seen.set(message, label);
    }
    expect(new Set(messages.map(([, message]) => message)).size).toBe(messages.length);
  });

  it("maps every stable code the contract and the boundary can return to reviewed copy", () => {
    for (const code of Object.keys(PROBLEM_CODE_KEYS)) {
      const view = say(code);

      expect(view.isGeneric, code).toBe(false);
      expect(view.message.length, code).toBeGreaterThan(10);
    }
  });

  it("gives an unknown code the generic sentence and a safe support reference, and never echoes the code", () => {
    const view = say("some_new_code_from_the_backend");

    expect(view.isGeneric).toBe(true);
    expect(view.message).toBe(en.problems.codes.unknown);
    expect(view.referenceLine).toContain("0198f1a2-7b3c-4d4e-8f5a-123456789abc");
    expect(JSON.stringify(view)).not.toContain("some_new_code");
  });

  it("adds the 'check before sending again' hint only where a mutation may have completed", () => {
    for (const code of [
      "upstream_timeout",
      "dependency_unavailable",
      "network_unavailable",
      "request_aborted",
      "internal_error"
    ]) {
      expect(say(code, { mutation: true }).mayHaveCompletedHint, code).toBe(
        en.problems.mayHaveCompleted
      );
      expect(say(code, { mutation: false }).mayHaveCompletedHint, code).toBeUndefined();
    }
    for (const code of [
      "validation_failed",
      "unauthenticated",
      "report_version_conflict",
      "rate_limited"
    ]) {
      expect(say(code, { mutation: true }).mayHaveCompletedHint, code).toBeUndefined();
    }
  });

  it("shows a support reference only for internal or unknown failures, and a wait time only when the API gave one", () => {
    expect(say("validation_failed").referenceLine).toBeUndefined();
    expect(say("internal_error").referenceLine).toBeDefined();
    const limited = describeProblem(
      problem("rate_limited", { retryAfterSeconds: 12 }),
      en.problems,
      lite
    );

    expect(limited.retryHint).toBeDefined();
    expect(say("rate_limited").retryHint).toBeUndefined();
  });
});
