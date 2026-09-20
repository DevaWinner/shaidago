import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { expect, it } from "vitest";

import { primitiveSheetMarkup } from "../support/primitives-sheet";

// Not a behavioural test: it renders every primitive with the real components to a static HTML
// fixture that the browser accessibility suite loads under the compiled stylesheet.
it("renders the primitive sheet fixture used by the browser accessibility suite", () => {
  const markup = primitiveSheetMarkup();
  const directory = join(import.meta.dirname, "..", ".generated");

  mkdirSync(directory, { recursive: true });
  writeFileSync(join(directory, "primitives-sheet.html"), markup);

  expect(markup).toContain("primitive-button--primary");
  expect(markup).toContain('role="switch"');
});
