import { isUuid } from "@/lib/identifiers";

/**
 * Client-side checking of a grounded answer. The API validates citations before it responds; this
 * repeats the one rule a resident's safety depends on, because a broken response must never be
 * shown as if it were sourced. An answer is shown only when every statement has at least one
 * citation and every citation resolves to a source returned in the same response. Anything else
 * fails closed and no statement text is rendered.
 *
 * The response shape is checked by hand, not with a schema library: this module ships to the
 * browser on every record page and a validator would cost more than the rest of the island.
 */

export const QUESTION_MAX = 300;

type Locale = "en" | "ha" | "ig" | "yo";
type Raw = Readonly<Record<string, unknown>>;
type RawSource = Readonly<{
  citation_id: string;
  passage: string;
  publisher: string;
  retrieved_at: string;
  section_label: string | null;
  source_id: string;
  title: string;
  url: string;
}>;
type RawAnswer = Readonly<{
  answer: string;
  confidence_note: string;
  generated_at: string;
  insufficient_evidence: boolean;
  requested_locale: Locale;
  retrieval: Readonly<{ chunks_considered: number; mode: "keyword" | "hybrid" }>;
  served_locale: Locale;
  sources: readonly RawSource[];
  statements: readonly Readonly<{ citation_ids: readonly string[]; text: string }>[];
}>;

const ISO_INSTANT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\d.]{0,10}(?:Z|[+-]\d{2}:\d{2})$/;

function isRecord(value: unknown): value is Raw {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function text(value: unknown, max: number): value is string {
  return typeof value === "string" && value.length <= max;
}

function isInstant(value: unknown): value is string {
  return text(value, 40) && ISO_INSTANT.test(value) && !Number.isNaN(Date.parse(value));
}

function isLocale(value: unknown): value is Locale {
  return value === "en" || value === "ha" || value === "ig" || value === "yo";
}

function isWebUrl(value: unknown): value is string {
  if (!text(value, 2048)) {
    return false;
  }

  try {
    const { protocol } = new URL(value);

    return protocol === "https:" || protocol === "http:";
  } catch {
    return false;
  }
}

function isSource(value: unknown): value is RawSource {
  return (
    isRecord(value) &&
    text(value["citation_id"], 200) &&
    value["citation_id"] !== "" &&
    text(value["passage"], 6000) &&
    text(value["publisher"], 300) &&
    isInstant(value["retrieved_at"]) &&
    (value["section_label"] === null || text(value["section_label"], 300)) &&
    text(value["source_id"], 36) &&
    isUuid(value["source_id"]) &&
    text(value["title"], 500) &&
    isWebUrl(value["url"])
  );
}

function isStatement(value: unknown): boolean {
  return (
    isRecord(value) &&
    text(value["text"], 4000) &&
    Array.isArray(value["citation_ids"]) &&
    value["citation_ids"].length <= 20 &&
    (value["citation_ids"] as unknown[]).every((id) => text(id, 200))
  );
}

function parseAnswer(value: unknown): RawAnswer | undefined {
  if (
    !isRecord(value) ||
    !text(value["answer"], 20000) ||
    !text(value["confidence_note"], 2000) ||
    !isInstant(value["generated_at"]) ||
    typeof value["insufficient_evidence"] !== "boolean" ||
    !isLocale(value["requested_locale"]) ||
    !isLocale(value["served_locale"]) ||
    !isRecord(value["retrieval"]) ||
    !Number.isInteger(value["retrieval"]["chunks_considered"]) ||
    Number(value["retrieval"]["chunks_considered"]) < 0 ||
    (value["retrieval"]["mode"] !== "keyword" && value["retrieval"]["mode"] !== "hybrid") ||
    !Array.isArray(value["sources"]) ||
    value["sources"].length > 50 ||
    !(value["sources"] as unknown[]).every(isSource) ||
    !Array.isArray(value["statements"]) ||
    value["statements"].length > 50 ||
    !(value["statements"] as unknown[]).every(isStatement)
  ) {
    return undefined;
  }

  // Every field of RawAnswer was checked above, so the assertion only names what was proven.
  return value as unknown as RawAnswer;
}

export type AnswerSource = Readonly<{
  number: number;
  citationId: string;
  passage: string;
  publisher: string;
  retrievedAt: string;
  sectionLabel: string | null;
  sourceId: string;
  title: string;
  url: string;
}>;

export type AnswerView = Readonly<{
  chunksConsidered: number;
  confidenceNote: string;
  generatedAt: string;
  mode: "keyword" | "hybrid";
  requestedLocale: "en" | "ha" | "ig" | "yo";
  servedLocale: "en" | "ha" | "ig" | "yo";
  sources: readonly AnswerSource[];
  statements: readonly Readonly<{ text: string; sources: readonly number[] }>[];
}>;

export type AnswerOutcome =
  | Readonly<{ kind: "supported"; view: AnswerView }>
  | Readonly<{
      kind: "insufficient";
      answer: string;
      confidenceNote: string;
      servedLocale: "en" | "ha" | "ig" | "yo";
    }>
  | Readonly<{ kind: "rejected" }>
  | Readonly<{ kind: "invalid" }>;

export function interpretAnswer(raw: unknown): AnswerOutcome {
  const answer = parseAnswer(raw);

  if (answer === undefined) {
    return { kind: "invalid" };
  }

  // Insufficient evidence carries no statements to show: whatever is attached is dropped.
  if (answer.insufficient_evidence) {
    return {
      kind: "insufficient",
      answer: answer.answer.trim(),
      confidenceNote: answer.confidence_note.trim(),
      servedLocale: answer.served_locale
    };
  }

  const byCitation = new Map<string, RawSource>();

  for (const source of answer.sources) {
    if (byCitation.has(source.citation_id)) {
      return { kind: "rejected" };
    }
    byCitation.set(source.citation_id, source);
  }

  if (answer.statements.length === 0) {
    return { kind: "rejected" };
  }

  const numbers = new Map<string, number>();
  const statements: { text: string; sources: number[] }[] = [];

  for (const statement of answer.statements) {
    if (statement.text.trim() === "" || statement.citation_ids.length === 0) {
      return { kind: "rejected" };
    }

    const cited: number[] = [];

    for (const id of statement.citation_ids) {
      if (!byCitation.has(id)) {
        return { kind: "rejected" };
      }
      if (!numbers.has(id)) {
        numbers.set(id, numbers.size + 1);
      }
      const number = numbers.get(id);

      if (number !== undefined && !cited.includes(number)) {
        cited.push(number);
      }
    }
    statements.push({ text: statement.text, sources: cited });
  }

  const sources: AnswerSource[] = [];

  for (const [id, number] of numbers) {
    const source = byCitation.get(id);

    if (source !== undefined) {
      sources.push({
        number,
        citationId: source.citation_id,
        passage: source.passage,
        publisher: source.publisher,
        retrievedAt: source.retrieved_at,
        sectionLabel: source.section_label,
        sourceId: source.source_id,
        title: source.title,
        url: source.url
      });
    }
  }

  return {
    kind: "supported",
    view: {
      chunksConsidered: answer.retrieval.chunks_considered,
      confidenceNote: answer.confidence_note.trim(),
      generatedAt: answer.generated_at,
      mode: answer.retrieval.mode,
      requestedLocale: answer.requested_locale,
      servedLocale: answer.served_locale,
      sources,
      statements
    }
  };
}
