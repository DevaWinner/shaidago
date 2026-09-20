export const LOCALES: readonly ["en", "ha", "ig", "yo"];

export function leaves(node: unknown, prefix?: readonly string[]): [string, unknown][];

export function describeMessage(source: string): {
  variables: Map<string, string>;
  selects: Map<string, string[]>;
  problems: string[];
};

export function checkCatalogues(input: {
  catalogues: Record<string, unknown>;
  status: unknown;
}): string[];

export function pendingKeys(input: {
  catalogues: Record<string, unknown>;
}): Record<string, string[]>;
