import { networkProblem, readBrowserProblem } from "@/lib/problems/browser-problem";
import type { SafeProblem } from "@/lib/problems/problem-messages";

/**
 * The browser side of the tracking and handle calls. Each call posts a JSON body to one fixed
 * same-origin path: a tracking code, handle, or passphrase is never in a path, query string, header,
 * or storage. Responses are checked by hand, not with a schema library, to keep the first load small.
 */

export type PostOutcome =
  | Readonly<{ kind: "ok"; status: number; data: unknown; replayed: boolean }>
  | Readonly<{ kind: "problem"; problem: SafeProblem }>
  | Readonly<{ kind: "network" }>
  | Readonly<{ kind: "aborted" }>;

export async function postJson(
  path: string,
  body: Readonly<Record<string, unknown>> | undefined,
  options: { locale: string; idempotencyKey?: string; signal?: AbortSignal }
): Promise<PostOutcome> {
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        "X-Shaidago-Locale": options.locale,
        ...(options.idempotencyKey === undefined
          ? {}
          : { "Idempotency-Key": options.idempotencyKey })
      },
      body: body === undefined ? null : JSON.stringify(body),
      cache: "no-store",
      credentials: "same-origin",
      ...(options.signal === undefined ? {} : { signal: options.signal })
    });

    if (!response.ok) {
      return { kind: "problem", problem: await readBrowserProblem(response) };
    }

    let data: unknown;

    if (response.status !== 204) {
      try {
        data = await response.json();
      } catch {
        return {
          kind: "problem",
          problem: {
            ...networkProblem(),
            code: "internal_error",
            status: response.status,
            requestId: response.headers.get("X-Request-Id") ?? undefined
          }
        };
      }
    }

    return {
      kind: "ok",
      status: response.status,
      data,
      replayed: response.headers.get("Idempotency-Replayed") === "true"
    };
  } catch (error) {
    return options.signal?.aborted === true ||
      (error instanceof DOMException && error.name === "AbortError")
      ? { kind: "aborted" }
      : { kind: "network" };
  }
}

export const STATUSES = [
  "received",
  "needs_information",
  "under_review",
  "verified_for_public_update",
  "referred",
  "closed"
] as const;
export type ReportStatus = (typeof STATUSES)[number];

export const NEXT_ACTIONS = [
  "wait_for_review",
  "answer_follow_up",
  "watch_public_updates",
  "see_escalation_guidance",
  "none"
] as const;
export type NextAction = (typeof NEXT_ACTIONS)[number];

export type QuestionState = "open" | "answered" | "skipped" | "unsafe";

export type StatusView = Readonly<{
  status: ReportStatus;
  updatedAt: string;
  message: string;
  nextAction: NextAction;
  questions: readonly Readonly<{ id: string; text: string; state: QuestionState }>[];
}>;

export type HandleItem = Readonly<{
  status: ReportStatus;
  updatedAt: string;
  message: string;
  nextAction: NextAction | undefined;
}>;

type Raw = Readonly<Record<string, unknown>>;

function isRecord(value: unknown): value is Raw {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isText(value: unknown, max: number): value is string {
  return typeof value === "string" && value.length <= max;
}

function isInstant(value: unknown): value is string {
  return isText(value, 40) && !Number.isNaN(Date.parse(value));
}

function oneOf<T extends string>(list: readonly T[], value: unknown): value is T {
  return typeof value === "string" && (list as readonly string[]).includes(value);
}

const QUESTION_STATES = ["open", "answered", "skipped", "unsafe"] as const;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** A status is trusted only in the documented shape; an unknown status is an unreadable response. */
export function parseStatus(value: unknown): StatusView | undefined {
  if (
    !isRecord(value) ||
    !oneOf(STATUSES, value["status"]) ||
    !isInstant(value["status_updated_at"]) ||
    !isText(value["message"], 2000) ||
    !oneOf(NEXT_ACTIONS, value["next_action"]) ||
    !Array.isArray(value["follow_up_questions"]) ||
    value["follow_up_questions"].length > 5
  ) {
    return undefined;
  }

  const questions: { id: string; text: string; state: QuestionState }[] = [];

  for (const item of value["follow_up_questions"] as unknown[]) {
    if (
      !isRecord(item) ||
      !isText(item["question_id"], 64) ||
      !UUID.test(item["question_id"]) ||
      !isText(item["text"], 1000) ||
      !oneOf(QUESTION_STATES, item["state"])
    ) {
      return undefined;
    }
    questions.push({ id: item["question_id"], text: item["text"], state: item["state"] });
  }

  return {
    status: value["status"],
    updatedAt: value["status_updated_at"],
    message: value["message"],
    nextAction: value["next_action"],
    questions
  };
}

export function parseHandleReports(value: unknown): readonly HandleItem[] | undefined {
  if (!isRecord(value) || !Array.isArray(value["reports"]) || value["reports"].length > 200) {
    return undefined;
  }

  const items: HandleItem[] = [];

  for (const item of value["reports"] as unknown[]) {
    if (
      !isRecord(item) ||
      !oneOf(STATUSES, item["status"]) ||
      !isInstant(item["status_updated_at"]) ||
      !isText(item["message"], 2000) ||
      !isText(item["next_action"], 64)
    ) {
      return undefined;
    }
    items.push({
      status: item["status"],
      updatedAt: item["status_updated_at"],
      message: item["message"],
      nextAction: oneOf(NEXT_ACTIONS, item["next_action"]) ? item["next_action"] : undefined
    });
  }

  return items;
}

export function parseHandleCreated(
  value: unknown
): Readonly<{ handle: string; passphrase: string }> | undefined {
  if (
    !isRecord(value) ||
    !isText(value["handle"], 200) ||
    value["handle"] === "" ||
    !isText(value["passphrase"], 400) ||
    value["passphrase"] === "" ||
    value["recoverable"] !== false
  ) {
    return undefined;
  }

  return { handle: value["handle"], passphrase: value["passphrase"] };
}

export function parseAck(value: unknown): "answered" | "skipped" | "unsafe" | undefined {
  return isRecord(value) &&
    value["acknowledged"] === true &&
    (value["question_state"] === "answered" ||
      value["question_state"] === "skipped" ||
      value["question_state"] === "unsafe")
    ? value["question_state"]
    : undefined;
}
