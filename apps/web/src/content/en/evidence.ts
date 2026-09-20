import type {
  DateGroupLabels,
  InformationClass,
  SourceAvailability,
  SourceCardLabels,
  TimelineOrigin,
  TranslationStatus,
  VerificationState
} from "@/components/evidence/evidence";

// English source copy for evidence states. The wording states what the record shows and never a
// verdict about a person or institution.
export const verificationLabels: Readonly<Record<VerificationState, string>> = {
  awaiting_verification: "Awaiting verification",
  verified_official: "Confirmed by an official source",
  corroborated: "Corroborated by more than one source",
  community_reviewed: "Reviewed community evidence",
  disputed: "Sources disagree",
  outdated: "May be out of date"
};

export const informationClassLabels: Readonly<Record<InformationClass, string>> = {
  official_source: "Official source",
  independent_source: "Independent source",
  community_evidence_reviewed: "Reviewed community evidence",
  community_report_unverified: "Community report, not verified",
  ai_generated_explanation: "AI-generated explanation, not a source"
};

export const availabilityLabels: Readonly<Record<SourceAvailability, string>> = {
  unchecked: "Not yet checked",
  available: "Available",
  temporarily_unavailable: "Temporarily unavailable",
  access_restricted: "Access restricted",
  permanently_unavailable: "No longer available"
};

export const dateGroupLabels: DateGroupLabels = {
  effective: "Effective",
  lastChecked: "Last checked",
  published: "Published",
  retrieved: "Retrieved",
  unknown: "Not recorded"
};

export const sourceCardLabels: SourceCardLabels = {
  availability: availabilityLabels,
  availabilityHeading: "Availability",
  classes: informationClassLabels,
  externalNotice: "opens the source in a new tab",
  publisherHeading: "Publisher"
};

export const translationStatusLabels: Readonly<Record<TranslationStatus, string>> = {
  reviewed: "Reviewed translation",
  machine_assisted: "Machine-assisted translation, not yet reviewed by a fluent reader",
  unavailable: "No translation available; showing the original"
};

export const timelineOriginLabels: Readonly<Record<TimelineOrigin, string>> = {
  official: "Official update",
  community_reviewed: "Reviewed community evidence"
};
