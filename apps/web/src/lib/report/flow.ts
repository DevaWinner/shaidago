/**
 * The report wizard as a pure state machine: which step follows which, what each step requires, and
 * which step a server-reported field belongs to. It holds no secrets of its own and touches no
 * storage; the component owns the values. Nothing here decides whether a report is acceptable: the
 * API does. These checks only stop an obviously incomplete step, and the API validates again.
 */

export const STEPS = ["notice", "observation", "evidence", "anonymity", "review"] as const;
export type Step = (typeof STEPS)[number];

export const CATEGORIES = [
  "no_visible_work",
  "incomplete_work",
  "unsafe_construction",
  "suspected_incorrect_status",
  "access_barrier",
  "other_concern"
] as const;
export type ConcernCategory = (typeof CATEGORIES)[number];

export const CHANNELS = ["email", "phone", "messaging_app"] as const;
export type ContactChannel = (typeof CHANNELS)[number];

export type IdentityMode = "anonymous" | "contact" | "handle";

export const LIMITS = {
  descriptionMin: 10,
  descriptionMax: 8000,
  contactMax: 200,
  handleMax: 200,
  passphraseMax: 200,
  files: 3,
  fileBytes: 10 * 1024 * 1024
} as const;

export type ReportForm = Readonly<{
  category: ConcernCategory | "";
  description: string;
  mode: IdentityMode;
  contactChannel: ContactChannel | "";
  contactValue: string;
  handle: string;
  passphrase: string;
}>;

export const EMPTY_FORM: ReportForm = {
  category: "",
  description: "",
  mode: "anonymous",
  contactChannel: "",
  contactValue: "",
  handle: "",
  passphrase: ""
};

export type FieldName =
  "category" | "description" | "contactChannel" | "contactValue" | "handle" | "passphrase";
export type ErrorKey =
  | "category"
  | "descriptionRequired"
  | "descriptionShort"
  | "descriptionLong"
  | "contact"
  | "channel"
  | "handle"
  | "passphrase";
export type StepError = Readonly<{ field: FieldName; key: ErrorKey }>;

const FIELD_STEP: Readonly<Record<FieldName, Step>> = {
  category: "observation",
  description: "observation",
  contactChannel: "anonymity",
  contactValue: "anonymity",
  handle: "anonymity",
  passphrase: "anonymity"
};

export function stepIndex(step: Step): number {
  return STEPS.indexOf(step);
}

export function nextStep(step: Step): Step {
  return STEPS[Math.min(stepIndex(step) + 1, STEPS.length - 1)] ?? "review";
}

export function previousStep(step: Step): Step {
  return STEPS[Math.max(stepIndex(step) - 1, 0)] ?? "notice";
}

function describe(form: ReportForm): StepError[] {
  const errors: StepError[] = [];

  if (form.category === "") {
    errors.push({ field: "category", key: "category" });
  }

  const length = form.description.trim().length;

  if (length === 0) {
    errors.push({ field: "description", key: "descriptionRequired" });
  } else if (length < LIMITS.descriptionMin) {
    errors.push({ field: "description", key: "descriptionShort" });
  } else if (form.description.length > LIMITS.descriptionMax) {
    errors.push({ field: "description", key: "descriptionLong" });
  }

  return errors;
}

function identify(form: ReportForm): StepError[] {
  const errors: StepError[] = [];

  if (form.mode === "contact") {
    if (form.contactChannel === "") {
      errors.push({ field: "contactChannel", key: "channel" });
    }
    if (form.contactValue.trim() === "") {
      errors.push({ field: "contactValue", key: "contact" });
    }
  }

  if (form.mode === "handle") {
    if (form.handle.trim() === "") {
      errors.push({ field: "handle", key: "handle" });
    }
    if (form.passphrase === "") {
      errors.push({ field: "passphrase", key: "passphrase" });
    }
  }

  return errors;
}

/** What must be fixed before leaving this step. The notice, evidence, and review steps need nothing. */
export function validateStep(step: Step, form: ReportForm): readonly StepError[] {
  if (step === "observation") {
    return describe(form);
  }

  return step === "anonymity" ? identify(form) : [];
}

/** The earliest step with a problem, so a review-time failure returns to where it can be fixed. */
export function firstInvalidStep(form: ReportForm): Step | undefined {
  return STEPS.find((step) => validateStep(step, form).length > 0);
}

/**
 * Switching identity mode deletes the other modes' values at once, so a contact detail or a
 * passphrase never lingers in memory after the person has chosen not to give it.
 */
export function withMode(form: ReportForm, mode: IdentityMode): ReportForm {
  return {
    ...form,
    mode,
    contactChannel: mode === "contact" ? form.contactChannel : "",
    contactValue: mode === "contact" ? form.contactValue : "",
    handle: mode === "handle" ? form.handle : "",
    passphrase: mode === "handle" ? form.passphrase : ""
  };
}

/** Maps an API field path (`body.description`, `concern_category`) to the step that owns it. */
export function stepForApiField(field: string): Step | undefined {
  const name = field.replace(/^(?:body|form|query)\./, "");

  if (name === "concern_category" || name === "description" || name === "project_slug") {
    return "observation";
  }
  if (name.startsWith("attachments")) {
    return "evidence";
  }
  if (name.startsWith("contact_") || name.startsWith("reporter_")) {
    return "anonymity";
  }

  return undefined;
}

export function stepForField(field: FieldName): Step {
  return FIELD_STEP[field];
}

/** True when leaving the page would lose something the person has written. */
export function hasContent(form: ReportForm, fileCount: number): boolean {
  return (
    form.category !== "" ||
    form.description.trim() !== "" ||
    fileCount > 0 ||
    form.contactValue.trim() !== "" ||
    form.handle.trim() !== "" ||
    form.passphrase !== ""
  );
}
