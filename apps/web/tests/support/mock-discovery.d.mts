export function sourceId(prefix: string, n: number): string;
export function defaultSources(prefix: string, reviewer: boolean): Record<string, unknown>[];
export function manySources(
  prefix: string,
  reviewer: boolean,
  count: number
): Record<string, unknown>[];
export function analysisFor(
  sources: Record<string, unknown>[],
  options?: { invalid?: boolean }
): { sources: { citation_id: string; source_id: string }[]; analysis: Record<string, unknown> };
