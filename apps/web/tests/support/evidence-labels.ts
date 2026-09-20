import type {
  DateGroupLabels,
  InformationClass,
  SourceAvailability,
  SourceCardLabels,
  TimelineOrigin,
  TranslationStatus,
  VerificationState
} from "@/components/evidence/evidence";

// Fictional English test labels. Real copy arrives with the reviewed message catalogues.
export const verificationLabels: Readonly<Record<VerificationState, string>> = {
  awaiting_verification: "Awaiting verification",
  verified_official: "Verified from an official source",
  corroborated: "Corroborated",
  community_reviewed: "Reviewed community evidence",
  disputed: "Disputed",
  outdated: "Outdated"
};

export const classLabels: Readonly<Record<InformationClass, string>> = {
  official_source: "Official source",
  independent_source: "Independent source",
  community_evidence_reviewed: "Reviewed community evidence",
  community_report_unverified: "Unverified community report",
  ai_generated_explanation: "AI-generated explanation"
};

export const availabilityLabels: Readonly<Record<SourceAvailability, string>> = {
  unchecked: "Not checked",
  available: "Available",
  temporarily_unavailable: "Temporarily unavailable",
  access_restricted: "Access restricted",
  permanently_unavailable: "No longer available"
};

export const dateLabels: DateGroupLabels = {
  effective: "Effective",
  lastChecked: "Last checked",
  published: "Published",
  retrieved: "Retrieved",
  unknown: "Not recorded"
};

export const sourceLabels: SourceCardLabels = {
  availability: availabilityLabels,
  availabilityHeading: "Availability",
  classes: classLabels,
  externalNotice: "opens the source in a new tab",
  publisherHeading: "Publisher",
  unknownDate: "Not recorded"
};

export const translationLabels: Readonly<Record<TranslationStatus, string>> = {
  reviewed: "Reviewed translation",
  machine_assisted: "Machine-assisted translation, not yet reviewed by a fluent reader",
  unavailable: "No translation available; showing the original"
};

export const originLabels: Readonly<Record<TimelineOrigin, string>> = {
  official: "Official update",
  community_reviewed: "Reviewed community evidence"
};

export const formatDate = (value: string): string => `on ${value.slice(0, 10)}`;
