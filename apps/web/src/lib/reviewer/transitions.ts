import type { components } from "@/lib/api/generated/schema";

export type TransitionCommand = components["schemas"]["TransitionRequest"]["command"];
/** The reporter-only `record_follow_up` is not something a reviewer can send. */
export type ReviewerCommand = Exclude<TransitionCommand, "record_follow_up">;
export type ReportStatus = components["schemas"]["TransitionRequest"]["expected_status"];

export type Transition = Readonly<{ command: ReviewerCommand; to: ReportStatus }>;

/**
 * The reviewer-usable commands from each status, mirroring the `report_status` machine in
 * `contracts/controlled-vocabulary.json` (a unit test compares the two, so drift fails). This is a
 * usability aid only: it hides commands that cannot apply. FastAPI remains the authority and still
 * answers `409 report_status_transition_not_allowed` for anything it refuses. The reporter-only
 * `record_follow_up` is deliberately absent.
 */
export const REVIEWER_TRANSITIONS: Readonly<Record<ReportStatus, readonly Transition[]>> = {
  received: [
    { command: "start_review", to: "under_review" },
    { command: "request_information", to: "needs_information" },
    { command: "close", to: "closed" }
  ],
  needs_information: [
    { command: "resume_review", to: "under_review" },
    { command: "close", to: "closed" }
  ],
  under_review: [
    { command: "request_information", to: "needs_information" },
    { command: "verify_for_public_update", to: "verified_for_public_update" },
    { command: "refer", to: "referred" },
    { command: "close", to: "closed" }
  ],
  verified_for_public_update: [
    { command: "resume_review", to: "under_review" },
    { command: "refer", to: "referred" },
    { command: "close", to: "closed" }
  ],
  referred: [
    { command: "resume_review", to: "under_review" },
    { command: "close", to: "closed" }
  ],
  closed: [{ command: "reopen", to: "under_review" }]
};

const STATUSES = Object.keys(REVIEWER_TRANSITIONS);

export function isReportStatus(value: string): value is ReportStatus {
  return STATUSES.includes(value);
}

/** Commands that materially change what the reporter or the case shows; they need a stronger warning. */
export const CONSEQUENTIAL: ReadonlySet<ReviewerCommand> = new Set([
  "close",
  "refer",
  "verify_for_public_update",
  "reopen",
  "request_information"
]);

/** The API requires an internal reason to reopen; the UI asks for it up front. */
export const NEEDS_REASON: ReadonlySet<ReviewerCommand> = new Set(["reopen"]);

/** Asking for information without saying what is needed would leave the reporter with nothing to do. */
export const NEEDS_MESSAGE: ReadonlySet<ReviewerCommand> = new Set(["request_information"]);

export function transitionsFrom(status: string): readonly Transition[] {
  return isReportStatus(status) ? REVIEWER_TRANSITIONS[status] : [];
}
