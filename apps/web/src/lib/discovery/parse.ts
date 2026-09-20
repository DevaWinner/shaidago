/**
 * Hand-written, strict readers for Source Scout run responses that arrive through the same-origin
 * handlers. The OpenAPI types describe `analysis` and `result` as free-form objects, so their
 * documented shape (`docs/IMPLEMENTATION_PLAN.md` and the replay fixtures under
 * `data/discovery-fixtures`) is checked here field by field. Anything that does not match is
 * refused, never rendered: an invalid analysis shows no analysis at all, and every source card
 * remains labelled `discovered — not yet reviewed` by our own copy, not by server text.
 */

export const MAX_SOURCES = 10;
export const MAX_FOLLOW_UPS = 5;

export type SourceView = Readonly<{
  id: string;
  title: string | null;
  /** `undefined` when the address is not a plain http(s) URL, so no link is ever rendered for it. */
  url: string | undefined;
  publisher: string;
  type: string;
  publishedOn: string | null;
  provenance: string;
  dateConflict: boolean;
  discoveredAt: string | undefined;
  retrievedAt: string | undefined;
  excerpt: string;
  availability: string;
  injectionFlag: boolean;
  disposition: string | undefined;
  duplicateKind: string | undefined;
  duplicateOf: string | undefined;
}>;

export type AnalysisView = Readonly<{
  facts: readonly Readonly<{ text: string; sources: readonly number[] }>[];
  claims: readonly Readonly<{ publisher: string; claim: string; source: number }>[];
  contradictions: readonly Readonly<{ description: string; sources: readonly number[] }>[];
  gaps: readonly string[];
  followUps: readonly Readonly<{ question: string; reason: string; sensitivity: string }>[];
  safety: string;
}>;

export type RunView = Readonly<{
  runId: string;
  status: string;
  version: number;
  scope: "public" | "reviewer";
  createdAt: string;
  finishedAt: string | null;
  demoReplay: boolean;
  failureCode: string | null;
  cancelRequested: boolean;
  queryText: string | null;
  counts: Readonly<{ found: number; fetched: number; analysed: number }>;
  sources: readonly SourceView[];
  analysis: AnalysisView | undefined;
}>;

type Rec = Readonly<Record<string, unknown>>;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const TOKEN = /^[a-z][a-z0-9_ -]{0,63}$/i;
const NO_NULL = /^[^\u0000]*$/;

const isRecord = (value: unknown): value is Rec =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const text = (value: unknown, max: number): value is string =>
  typeof value === "string" && value.length <= max && NO_NULL.test(value);
const count = (value: unknown): value is number =>
  typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 1_000_000;
const isoDate = (value: unknown): value is string =>
  typeof value === "string" && !Number.isNaN(Date.parse(value));

export function safeHttpUrl(value: unknown): string | undefined {
  if (typeof value !== "string" || value.length > 2000) {
    return undefined;
  }

  try {
    const parsed = new URL(value);

    return (parsed.protocol === "https:" || parsed.protocol === "http:") &&
      parsed.username === "" &&
      parsed.password === ""
      ? parsed.toString()
      : undefined;
  } catch {
    return undefined;
  }
}

function parseSource(value: unknown): SourceView | undefined {
  if (
    !isRecord(value) ||
    typeof value["source_id"] !== "string" ||
    !UUID.test(value["source_id"]) ||
    !(value["title"] === null || text(value["title"], 300)) ||
    !text(value["publisher_domain"], 253) ||
    !text(value["preliminary_type"], 80) ||
    !text(value["excerpt"], 2000) ||
    !text(value["availability"], 60) ||
    !text(value["published_provenance"], 120) ||
    typeof value["date_conflict"] !== "boolean" ||
    !(value["published_on"] === null || text(value["published_on"], 10))
  ) {
    return undefined;
  }

  const optional = (key: string): string | undefined =>
    typeof value[key] === "string" && text(value[key], 80) ? (value[key] as string) : undefined;
  const duplicateOf =
    typeof value["duplicate_of"] === "string" && UUID.test(value["duplicate_of"])
      ? value["duplicate_of"]
      : undefined;

  return {
    id: value["source_id"],
    title: value["title"] as string | null,
    url: safeHttpUrl(value["canonical_url"]),
    publisher: value["publisher_domain"],
    type: value["preliminary_type"],
    publishedOn: value["published_on"] as string | null,
    provenance: value["published_provenance"],
    dateConflict: value["date_conflict"],
    discoveredAt: isoDate(value["first_discovered_at"]) ? value["first_discovered_at"] : undefined,
    retrievedAt: isoDate(value["last_retrieved_at"]) ? value["last_retrieved_at"] : undefined,
    excerpt: value["excerpt"],
    availability: value["availability"],
    injectionFlag: value["injection_flag"] === true,
    disposition: optional("disposition"),
    duplicateKind: optional("duplicate_kind"),
    duplicateOf
  };
}

export function parseSources(value: unknown): readonly SourceView[] | undefined {
  if (!Array.isArray(value) || value.length > MAX_SOURCES) {
    return undefined;
  }

  const sources: SourceView[] = [];

  for (const item of value as unknown[]) {
    const source = parseSource(item);

    if (source === undefined) {
      return undefined;
    }
    sources.push(source);
  }

  return sources;
}

/**
 * Every citation must resolve to a source card of this same run, contradictions need two sides,
 * and a supported fact needs at least one citation; otherwise there is no analysis to show.
 */
export function parseAnalysis(
  envelope: unknown,
  sources: readonly SourceView[]
): AnalysisView | undefined {
  if (
    !isRecord(envelope) ||
    !isRecord(envelope["analysis"]) ||
    !Array.isArray(envelope["sources"])
  ) {
    return undefined;
  }

  const body = envelope["analysis"];
  const citations = new Map<string, number>();

  for (const item of envelope["sources"] as unknown[]) {
    if (
      !isRecord(item) ||
      !text(item["citation_id"], 64) ||
      typeof item["source_id"] !== "string"
    ) {
      return undefined;
    }

    const index = sources.findIndex((source) => source.id === item["source_id"]);

    if (index < 0 || citations.has(item["citation_id"])) {
      return undefined;
    }
    citations.set(item["citation_id"], index);
  }

  const resolve = (ids: unknown, min: number, max: number): number[] | undefined => {
    if (!Array.isArray(ids) || ids.length < min || ids.length > max) {
      return undefined;
    }

    const out: number[] = [];

    for (const id of ids as unknown[]) {
      const index = typeof id === "string" ? citations.get(id) : undefined;

      if (index === undefined) {
        return undefined;
      }
      out.push(index);
    }

    return out;
  };

  const facts = body["supported_facts"];
  const claims = body["reported_claims"];
  const contradictions = body["contradictions"];
  const gaps = body["information_gaps"];
  const questions = body["follow_up_questions"] ?? [];

  if (
    !Array.isArray(facts) ||
    facts.length > 8 ||
    !Array.isArray(claims) ||
    claims.length > 10 ||
    !Array.isArray(contradictions) ||
    contradictions.length > 10 ||
    !Array.isArray(gaps) ||
    gaps.length > 10 ||
    !Array.isArray(questions) ||
    questions.length > MAX_FOLLOW_UPS ||
    !text(body["safety_note"], 400)
  ) {
    return undefined;
  }

  const parsedFacts: { text: string; sources: number[] }[] = [];
  const parsedClaims: { publisher: string; claim: string; source: number }[] = [];
  const parsedContradictions: { description: string; sources: number[] }[] = [];
  const parsedQuestions: { question: string; reason: string; sensitivity: string }[] = [];

  for (const item of facts as unknown[]) {
    const ids = isRecord(item) ? resolve(item["citation_ids"], 1, 3) : undefined;

    if (!isRecord(item) || !text(item["text"], 400) || ids === undefined) {
      return undefined;
    }
    parsedFacts.push({ text: item["text"], sources: ids });
  }
  for (const item of claims as unknown[]) {
    const ids = isRecord(item) ? resolve([item["citation_id"]], 1, 1) : undefined;

    if (
      !isRecord(item) ||
      !text(item["publisher"], 200) ||
      !text(item["claim"], 400) ||
      ids?.[0] === undefined
    ) {
      return undefined;
    }
    parsedClaims.push({ publisher: item["publisher"], claim: item["claim"], source: ids[0] });
  }
  for (const item of contradictions as unknown[]) {
    const ids = isRecord(item) ? resolve(item["citation_ids"], 2, 4) : undefined;

    if (!isRecord(item) || !text(item["description"], 400) || ids === undefined) {
      return undefined;
    }
    parsedContradictions.push({ description: item["description"], sources: ids });
  }
  if (!(gaps as unknown[]).every((gap) => text(gap, 240))) {
    return undefined;
  }
  for (const item of questions as unknown[]) {
    if (
      !isRecord(item) ||
      !text(item["question"], 500) ||
      !text(item["reason"], 400) ||
      typeof item["sensitivity"] !== "string" ||
      !TOKEN.test(item["sensitivity"])
    ) {
      return undefined;
    }
    parsedQuestions.push({
      question: item["question"],
      reason: item["reason"],
      sensitivity: item["sensitivity"]
    });
  }

  return {
    facts: parsedFacts,
    claims: parsedClaims,
    contradictions: parsedContradictions,
    gaps: gaps as string[],
    followUps: parsedQuestions,
    safety: body["safety_note"]
  };
}

/** Public runs carry the analysis in `result` and reviewer runs in `analysis`; both share a shape. */
export function parseRun(value: unknown, scope: "public" | "reviewer"): RunView | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const sources = parseSources(value["sources"]);
  const publicProgress = isRecord(value["progress"]) ? value["progress"] : undefined;
  const counts =
    scope === "public"
      ? publicProgress === undefined
        ? undefined
        : {
            found: publicProgress["results_found"],
            fetched: publicProgress["fetched"],
            analysed: publicProgress["analysed"]
          }
      : {
          found: value["results_found"],
          fetched: value["fetched_count"],
          analysed: value["analysed_count"]
        };

  if (
    sources === undefined ||
    counts === undefined ||
    !count(counts.found) ||
    !count(counts.fetched) ||
    !count(counts.analysed) ||
    typeof value["run_id"] !== "string" ||
    !UUID.test(value["run_id"]) ||
    !text(value["status"], 40) ||
    !count(value["version"]) ||
    !isoDate(value["created_at"]) ||
    !(value["finished_at"] === null || isoDate(value["finished_at"])) ||
    typeof value["demo_replay"] !== "boolean" ||
    !(
      value["failure_code"] === null ||
      (typeof value["failure_code"] === "string" && TOKEN.test(value["failure_code"]))
    )
  ) {
    return undefined;
  }

  const envelope = scope === "public" ? value["result"] : value["analysis"];
  const queryText = value["query_text"];

  return {
    runId: value["run_id"],
    status: value["status"],
    version: value["version"],
    scope,
    createdAt: value["created_at"],
    finishedAt: value["finished_at"] as string | null,
    demoReplay: value["demo_replay"],
    failureCode: value["failure_code"] as string | null,
    cancelRequested: value["cancel_requested"] === true,
    queryText: scope === "reviewer" && text(queryText, 400) ? queryText : null,
    counts: { found: counts.found, fetched: counts.fetched, analysed: counts.analysed },
    sources,
    analysis: isRecord(envelope) ? parseAnalysis(envelope, sources) : undefined
  };
}

/** Sources that repeat another source are grouped under it, in the order the API returned them. */
export function groupDuplicates(
  sources: readonly SourceView[]
): readonly Readonly<{ primary: SourceView; duplicates: readonly SourceView[] }>[] {
  const ids = new Set(sources.map((source) => source.id));
  const primaries = sources.filter(
    (source) => source.duplicateOf === undefined || !ids.has(source.duplicateOf)
  );

  return primaries.map((primary) => ({
    primary,
    duplicates: sources.filter((source) => source.duplicateOf === primary.id)
  }));
}
