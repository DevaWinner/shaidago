import type { components } from "@/lib/api/generated/schema";
import type { ProjectDetail, ProjectUpdate } from "@/lib/api/public-data";

export type PreviewIssue = Readonly<{ field: string; code: string }>;

export type PreviewView = Readonly<{
  id: string;
  state: string;
  projectSlug: string;
  reportStatus: string;
  reportVersion: number;
  update: ProjectUpdate;
  issues: readonly PreviewIssue[];
  canPublish: boolean;
  digest: string;
}>;

export type CitationOption = Readonly<{
  key: string;
  sourceVersionId: string;
  passage: string;
  locationLabel: string;
  publisher: string;
  sourceTitle: string;
}>;

const MAX_OPTIONS = 40;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DIGEST = /^[0-9a-f]{64}$/;
const VERIFICATION = [
  "awaiting_verification",
  "verified_official",
  "corroborated",
  "community_reviewed",
  "disputed",
  "outdated"
] as const;
const CLASSES = ["official_source", "independent_source", "community_evidence_reviewed"] as const;

type Citation = components["schemas"]["CitationOut"];

const isRecord = (value: unknown): value is Readonly<Record<string, unknown>> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const text = (value: unknown, max = 5000): value is string =>
  typeof value === "string" && value.length <= max;

function parseCitation(value: unknown): Citation | undefined {
  if (
    !isRecord(value) ||
    !text(value["canonical_url"], 2000) ||
    !text(value["location_label"], 500) ||
    !text(value["passage"]) ||
    !text(value["publisher"], 500) ||
    !text(value["retrieved_at"], 40) ||
    !text(value["source_id"], 40) ||
    !text(value["source_title"], 500) ||
    !text(value["source_type"], 100) ||
    typeof value["source_version_id"] !== "string" ||
    !UUID.test(value["source_version_id"]) ||
    !CLASSES.some((item) => item === value["information_class"])
  ) {
    return undefined;
  }

  return value as Citation;
}

/**
 * Reads a preview from the same-origin handler by hand, so a malformed or unexpected body is
 * refused rather than rendered. The result is the public update exactly as the API describes it,
 * which is what the shared public timeline entry then renders.
 */
export function parsePreview(value: unknown): PreviewView | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const update = value["update"];
  const issues = value["issues"];

  if (
    typeof value["public_update_id"] !== "string" ||
    !UUID.test(value["public_update_id"]) ||
    !text(value["state"], 40) ||
    !text(value["project_slug"], 120) ||
    !text(value["report_status"], 60) ||
    !Number.isInteger(value["report_version"]) ||
    typeof value["can_publish"] !== "boolean" ||
    typeof value["preview_digest"] !== "string" ||
    !DIGEST.test(value["preview_digest"]) ||
    !isRecord(update) ||
    !Array.isArray(issues) ||
    issues.length > 50
  ) {
    return undefined;
  }

  const citations = Array.isArray(update["citations"])
    ? (update["citations"] as unknown[]).map(parseCitation)
    : undefined;

  if (
    citations === undefined ||
    citations.length > 5 ||
    citations.some((item) => item === undefined) ||
    typeof update["id"] !== "string" ||
    !UUID.test(update["id"]) ||
    !text(update["statement"], 5000) ||
    !(update["effective_on"] === null || text(update["effective_on"], 10)) ||
    !(update["last_checked_on"] === null || text(update["last_checked_on"], 10)) ||
    !VERIFICATION.some((item) => item === update["verification_state"]) ||
    !CLASSES.some((item) => item === update["information_class"]) ||
    update["ai_generated"] !== false
  ) {
    return undefined;
  }

  const parsedIssues: PreviewIssue[] = [];

  for (const issue of issues as unknown[]) {
    if (!isRecord(issue) || !text(issue["field"], 100) || !text(issue["code"], 100)) {
      return undefined;
    }
    parsedIssues.push({ field: issue["field"], code: issue["code"] });
  }

  return {
    id: value["public_update_id"],
    state: value["state"],
    projectSlug: value["project_slug"],
    reportStatus: value["report_status"],
    reportVersion: value["report_version"] as number,
    update: { ...(update as ProjectUpdate), citations: citations as Citation[] },
    issues: parsedIssues,
    canPublish: value["can_publish"],
    digest: value["preview_digest"]
  };
}

/**
 * The approved citations a reviewer may attach: exactly those the public record for the report's
 * own project already shows, so a passage is copied verbatim from an approved source version and
 * never typed. Nothing from the private report can become a citation, and a project with none
 * offers none (the composer then refuses to draft).
 */
export function citationOptions(project: ProjectDetail): readonly CitationOption[] {
  const seen = new Map<string, CitationOption>();

  for (const statement of [...project.facts, ...project.updates]) {
    for (const citation of statement.citations) {
      const key = `${citation.source_version_id}|${citation.location_label}|${citation.passage}`;

      if (!seen.has(key) && seen.size < MAX_OPTIONS) {
        seen.set(key, {
          key,
          sourceVersionId: citation.source_version_id,
          passage: citation.passage,
          locationLabel: citation.location_label,
          publisher: citation.publisher,
          sourceTitle: citation.source_title
        });
      }
    }
  }

  return [...seen.values()];
}

const ISSUE_PREFIX = "unsupported_term_";

/** Maps an issue code to a key of the publication copy, or a term for the "unsupported word" text. */
export function issueKind(
  code: string
): { kind: "term"; term: string } | { kind: "known"; key: string } | { kind: "other" } {
  if (code.startsWith(ISSUE_PREFIX) && /^[a-z]{2,30}$/.test(code.slice(ISSUE_PREFIX.length))) {
    return { kind: "term", term: code.slice(ISSUE_PREFIX.length) };
  }
  if (/^[a-z_]{2,60}$/.test(code)) {
    return { kind: "known", key: code };
  }

  return { kind: "other" };
}
