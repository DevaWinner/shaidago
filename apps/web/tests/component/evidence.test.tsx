import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  AiExplanationNotice,
  CitationEntry,
  ClaimWithCitations,
  DateGroup,
  EvidenceGap,
  InformationClassMarker,
  SourceCard,
  TimelineItem,
  TranslationNotice,
  VerificationLabel,
  type CitationView,
  type VerificationState
} from "@/components/evidence/evidence";
import {
  classLabels,
  dateLabels,
  formatDate,
  originLabels,
  sourceLabels,
  translationLabels,
  verificationLabels
} from "../support/evidence-labels";

const citation: CitationView = {
  id: "c1",
  label: "Source 1",
  locationLabel: "section 2",
  passage: "An invented passage of a fictional record.",
  publisher: "Synthetic Publisher",
  sourceTitle: "Synthetic Record"
};

describe("verification and class markers", () => {
  it.each(Object.keys(verificationLabels) as VerificationState[])(
    "states %s in words with a decorative shape",
    (state) => {
      const { container } = render(<VerificationLabel labels={verificationLabels} state={state} />);
      expect(screen.getByText(verificationLabels[state])).toBeVisible();
      expect(container.querySelector("[aria-hidden='true']")).not.toBeNull();
    }
  );

  it("never derives a verification state from the number of sources", () => {
    render(
      <>
        <ClaimWithCitations
          citations={[citation, { ...citation, id: "c2", label: "Source 2" }]}
          citedLabel="Sources"
          claimId="f1"
          verification={
            <VerificationLabel labels={verificationLabels} state="awaiting_verification" />
          }
        >
          Two sources exist for this claim.
        </ClaimWithCitations>
      </>
    );
    expect(screen.getByText("Awaiting verification")).toBeVisible();
    expect(screen.queryByText(/Verified/)).toBeNull();
  });

  it("names every information class, including AI and unverified community text", () => {
    render(
      <>
        <InformationClassMarker labels={classLabels} value="ai_generated_explanation" />
        <InformationClassMarker labels={classLabels} value="community_report_unverified" />
      </>
    );
    expect(screen.getByText("AI-generated explanation")).toBeVisible();
    expect(screen.getByText("Unverified community report")).toBeVisible();
  });
});

describe("dates", () => {
  it("shows the mandatory last-checked date as unknown when absent, and omits other absent dates", () => {
    render(<DateGroup dates={{ effectiveOn: null }} format={formatDate} labels={dateLabels} />);
    expect(screen.getByText("Last checked").nextElementSibling).toHaveTextContent("Not recorded");
    expect(screen.queryByText("Effective")).toBeNull();
    expect(screen.queryByText("Retrieved")).toBeNull();
  });

  it("renders supplied dates as machine-readable time elements", () => {
    render(
      <DateGroup
        dates={{
          lastCheckedOn: "2026-09-01",
          effectiveOn: "2026-08-15",
          retrievedAt: "2026-09-03T09:00:00Z"
        }}
        format={formatDate}
        labels={dateLabels}
      />
    );
    const checked = screen.getByText("on 2026-09-01");
    expect(checked.tagName).toBe("TIME");
    expect(checked).toHaveAttribute("datetime", "2026-09-01");
    expect(screen.getByText("Retrieved").nextElementSibling).toHaveTextContent("on 2026-09-03");
  });
});

describe("source card", () => {
  const source = {
    availability: "temporarily_unavailable",
    availabilityCheckedAt: "2026-09-02T10:00:00Z",
    canonicalUrl: "https://synthetic.example/record",
    id: "s1",
    informationClass: "official_source",
    publisher: "Synthetic Publisher",
    title: "Synthetic Record"
  } as const;

  it("links to the original source safely and states availability with its check date", () => {
    render(<SourceCard format={formatDate} labels={sourceLabels} source={source} />);
    const link = screen.getByRole("link", { name: /Synthetic Record/ });
    expect(link).toHaveAttribute("href", "https://synthetic.example/record");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAccessibleName("Synthetic Record (opens the source in a new tab)");
    expect(screen.getByText(/Temporarily unavailable/)).toBeVisible();
    expect(screen.getByText("Official source")).toBeVisible();
    expect(document.getElementById("source-s1")).not.toBeNull();
  });

  it("omits the check date when none is recorded", () => {
    render(
      <SourceCard
        format={formatDate}
        labels={sourceLabels}
        source={{ ...source, availability: "unchecked", availabilityCheckedAt: null }}
      />
    );
    expect(screen.getByText("Not checked").querySelector("time")).toBeNull();
  });
});

describe("claims and the citation stitch", () => {
  it("links each citation control to its entry with the same identifier, using plain anchors", () => {
    render(
      <>
        <ClaimWithCitations citations={[citation]} citedLabel="Sources for this claim" claimId="f1">
          The project promised a clinic.
        </ClaimWithCitations>
        <ol>
          <CitationEntry backHref="#claim-f1" backLabel="Back to claim" citation={citation} />
        </ol>
      </>
    );

    const trigger = within(screen.getByRole("list", { name: "Sources for this claim" })).getByRole(
      "link",
      {
        name: "Source 1"
      }
    );
    expect(trigger).toHaveAttribute("href", "#citation-c1");
    expect(trigger).toHaveAccessibleDescription(/An invented passage/);
    expect(document.getElementById("citation-c1")).toHaveAttribute("tabindex", "-1");
    expect(screen.getByRole("link", { name: "Back to claim" })).toHaveAttribute(
      "href",
      "#claim-f1"
    );
    expect(screen.getByText("An invented passage of a fictional record.").tagName).toBe(
      "BLOCKQUOTE"
    );
  });

  it("refuses to render a claim that has no citation", () => {
    const { container } = render(
      <ClaimWithCitations citations={[]} citedLabel="Sources" claimId="f2">
        An uncited public claim.
      </ClaimWithCitations>
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("timeline, notices, and gaps", () => {
  it("separates official from reviewed-community entries by words", () => {
    render(
      <ol>
        <TimelineItem
          date="2026-09-01"
          dateLabel="Effective"
          format={formatDate}
          origin="official"
          originLabels={originLabels}
          verification={<VerificationLabel labels={verificationLabels} state="verified_official" />}
        >
          Contract signed.
        </TimelineItem>
        <TimelineItem
          date={null}
          dateLabel="Effective"
          format={formatDate}
          origin="community_reviewed"
          originLabels={originLabels}
          verification={
            <VerificationLabel labels={verificationLabels} state="community_reviewed" />
          }
        >
          Site visit noted.
        </TimelineItem>
      </ol>
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Official update")).toBeVisible();
    expect(screen.getAllByText("Reviewed community evidence").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Effective/)).toHaveLength(1);
  });

  it("warns only when a translation is not reviewed", () => {
    const { rerender } = render(<TranslationNotice labels={translationLabels} status="reviewed" />);
    expect(screen.queryByRole("note")).toBeNull();
    rerender(<TranslationNotice labels={translationLabels} status="machine_assisted" />);
    expect(screen.getByRole("note")).toHaveTextContent("Machine-assisted translation");
    rerender(<TranslationNotice labels={translationLabels} status="unavailable" />);
    expect(screen.getByRole("note")).toHaveTextContent("showing the original");
  });

  it("labels AI text as an explanation and distinguishes the three evidence gaps", () => {
    render(
      <>
        <AiExplanationNotice label="AI-generated explanation, not a source">
          A plain-language summary.
        </AiExplanationNotice>
        <EvidenceGap kind="contradiction" title="Sources disagree">
          One says complete, one says in progress.
        </EvidenceGap>
        <EvidenceGap kind="information_gap" title="Not yet known" />
        <EvidenceGap kind="insufficient_evidence" title="Not enough evidence to answer" />
      </>
    );
    expect(screen.getAllByRole("note")).toHaveLength(4);
    expect(screen.getByText("AI-generated explanation, not a source")).toBeVisible();
    expect(screen.getByText("Sources disagree")).toBeVisible();
    expect(screen.getByText("Not yet known")).toBeVisible();
    expect(screen.getByText("Not enough evidence to answer")).toBeVisible();
  });
});
