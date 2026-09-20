import type { PublicShellMessages, ReviewerShellMessages } from "@/components/shell/shell";

// English source copy. Hausa, Igbo, and Yoruba records join the shared catalogue in FE-051 and
// must come from fluent, reviewed translation; nothing here is machine-translated into them.
export const publicShellMessages: PublicShellMessages = {
  footerLabel: "About ShaidaGo",
  footerSources: "How sources are approved",
  footerTrust: "How to read a record",
  localeCurrentSuffix: "current language",
  localeLabel: "Language",
  localeNames: { en: "English", ha: "Hausa", ig: "Igbo", yo: "Yorùbá" },
  localeUnavailable: "not yet reviewed",
  navLabel: "Main",
  navLocalities: "Localities",
  navReport: "Report a concern",
  navTrust: "How records work",
  notEmergency:
    "ShaidaGo is not an emergency service. If someone is in danger, contact local emergency services first.",
  productName: "ShaidaGo",
  skipToContent: "Skip to main content",
  statusRegionLabel: "Connection and page status"
};

export const reviewerShellMessages: ReviewerShellMessages = {
  area: "Reviewer",
  navLabel: "Reviewer",
  productName: "ShaidaGo",
  queue: "Report queue",
  skipToContent: "Skip to main content"
};
