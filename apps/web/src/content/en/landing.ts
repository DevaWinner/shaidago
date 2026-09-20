// English source copy for the landing first viewport. The sample record is invented for layout
// and says so on the page; real records come from approved public sources through the API.
export const landingMessages = {
  browse: "Browse project records",
  citedLabel: "Sources for this statement",
  citationBack: "Back to the statement",
  evidenceHeading: "Dated evidence",
  heading: "Public project records for AMAC and Bwari, with their sources",
  lead: "Each record shows what was promised, what the sources say, when it was last checked, and what is still unknown.",
  localityLabel: "Example locality",
  recordKind: "Public project record",
  report: "Report a concern privately",
  reportNote: "Reports are private and are never published automatically.",
  sample: {
    citation: {
      locationLabel: "example section",
      passage:
        "Example passage: the clinic refurbishment is listed as planned for the coming year.",
      publisher: "Example publisher",
      sourceTitle: "Example planning notice"
    },
    heading: "Example: ward health clinic refurbishment",
    notice:
      "Fictional example. This shows how a record is laid out; it is not a real project or source.",
    noticeTitle: "Example only",
    promised: "Promised: a refurbished ward health clinic.",
    railEntries: {
      community: "A visit note was received and is waiting for review.",
      official: "The planning notice lists the clinic as planned."
    },
    sourceCount: "1 source",
    sourceCountLabel: "Sources",
    stateLabel: "Current known state",
    stateText: "Listed as planned. Progress has not been confirmed."
  }
} as const;
