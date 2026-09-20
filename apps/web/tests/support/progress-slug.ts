import type { TestInfo } from "@playwright/test";

/** Each browser project follows its own progressing public run, so parallel runs never share stages. */
export const progressSlug = (info: TestInfo): string =>
  info.project.name === "chromium" ? "synthetic-project-04" : "synthetic-project-06";
