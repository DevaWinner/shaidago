import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

// @ts-expect-error -- plain ESM script shared with the CLI; it has no type declarations.
import { LOCALES, checkCatalogues, describeMessage } from "../../scripts/messages-parity.mjs";
import { contentLocale, REVIEWED_LOCALES } from "@/i18n/routing";

type Json = Record<string, unknown>;
const root = join(import.meta.dirname, "..", "..", "messages");
const read = (name: string): Json =>
  JSON.parse(readFileSync(join(root, `${name}.json`), "utf8")) as Json;

function fixture(): { catalogues: Record<string, Json>; status: Json } {
  const en: Json = {
    shell: { greeting: "Hello {name}", count: "{count, plural, one {# item} other {# items}}" },
    landing: { title: "Title", kind: "{kind, select, a {A} b {B} other {C}}" }
  };
  const blank = (): Json => ({
    shell: { greeting: null, count: null },
    landing: { title: null, kind: null }
  });
  const reviewed = { status: "reviewed", reviewer: "maintainer", reviewedOn: "2026-09-20" };
  const pending = { status: "pending" };

  return {
    catalogues: { en, ha: blank(), ig: blank(), yo: blank() },
    status: {
      domains: { shell: { critical: true }, landing: { critical: false } },
      locales: {
        en: { shell: reviewed, landing: reviewed },
        ha: { shell: pending, landing: pending },
        ig: { shell: pending, landing: pending },
        yo: { shell: pending, landing: pending }
      }
    }
  };
}

function errorsFor(mutate: (input: ReturnType<typeof fixture>) => void): string[] {
  const input = fixture();
  mutate(input);

  return checkCatalogues(input) as string[];
}

const translate = (
  input: ReturnType<typeof fixture>,
  locale: string,
  shell: Json,
  landing?: Json
) => {
  input.catalogues[locale] = {
    shell,
    landing: landing ?? { title: "T", kind: "{kind, select, a {A} b {B} other {C}}" }
  };
  const reviewedRecord = {
    status: "machine_assisted",
    reviewer: "tester",
    reviewedOn: "2026-09-20"
  };
  const locales = input.status["locales"] as Record<string, Json>;
  locales[locale] = { shell: reviewedRecord, landing: reviewedRecord };
};

describe("real catalogues", () => {
  it("are consistent and cover the four public locales", () => {
    const catalogues = Object.fromEntries(
      (LOCALES as string[]).map((locale) => [locale, read(locale)])
    );

    expect(LOCALES).toEqual(["en", "ha", "ig", "yo"]);
    expect(checkCatalogues({ catalogues, status: read("status") })).toEqual([]);
  });

  it("serve English as reviewed source and mark the other locales pending, so they are not served as their own language", () => {
    const status = read("status") as {
      locales: Record<string, Record<string, { status: string }>>;
    };

    expect(
      Object.values(status.locales["en"] ?? {}).every((domain) => domain.status === "reviewed")
    ).toBe(true);
    for (const locale of ["ha", "ig", "yo"]) {
      expect(
        Object.values(status.locales[locale] ?? {}).every((domain) => domain.status === "pending")
      ).toBe(true);
    }
    expect([...REVIEWED_LOCALES]).toEqual(["en"]);
    expect(contentLocale("yo")).toBe("en");
  });
});

describe("structure", () => {
  it("accepts a consistent set of pending catalogues", () => {
    expect(errorsFor(() => undefined)).toEqual([]);
  });

  it("reports missing keys, extra keys, and shape mismatches", () => {
    expect(
      errorsFor((input) => delete (input.catalogues["ha"]?.["shell"] as Json)["greeting"])
    ).toContain('ha: missing key "shell.greeting"');
    expect(
      errorsFor((input) => ((input.catalogues["ig"]?.["shell"] as Json)["extra"] = null))
    ).toContain('ig: extra key "shell.extra" not in en');
    expect(
      errorsFor(
        (input) =>
          ((input.catalogues["yo"] as Json)["shell"] = { greeting: { nested: null }, count: null })
      )
    ).toContain('yo: "shell.greeting" is a leaf in en but not here');
    expect(errorsFor((input) => delete input.catalogues["yo"])).toContain(
      "yo: catalogue is missing or not an object"
    );
  });

  it("rejects empty, blank, and non-string leaves", () => {
    for (const bad of ["", "   ", 5, true]) {
      const errors = errorsFor(
        (input) => ((input.catalogues["ha"]?.["landing"] as Json)["title"] = bad)
      );

      expect(
        errors.some((error) =>
          error.includes('ha: "landing.title" must be a non-empty string or null')
        ),
        String(bad)
      ).toBe(true);
    }
    expect(
      errorsFor((input) => ((input.catalogues["en"]?.["landing"] as Json)["title"] = ""))
    ).toContain('en: "landing.title" must be a non-empty string');
  });
});

describe("ICU syntax and variables", () => {
  it("rejects invalid ICU in English and in a translation", () => {
    expect(
      errorsFor(
        (input) => ((input.catalogues["en"]?.["shell"] as Json)["greeting"] = "Hello {name")
      ).some((error) => error.startsWith('en: "shell.greeting" is not valid ICU'))
    ).toBe(true);
    expect(
      errorsFor((input) =>
        translate(input, "ha", {
          greeting: "Sannu {name",
          count: "{count, plural, one {# a} other {# b}}"
        })
      ).some((error) => error.startsWith('ha: "shell.greeting" is not valid ICU'))
    ).toBe(true);
  });

  it("requires the same variable names in a translation", () => {
    const errors = errorsFor((input) =>
      translate(input, "ha", {
        greeting: "Sannu {person}",
        count: "{count, plural, one {# a} other {# b}}"
      })
    );

    expect(errors).toContain('ha: "shell.greeting" is missing variable "name"');
    expect(errors).toContain('ha: "shell.greeting" has variable "person" that en does not');
  });

  it("requires the same variable types", () => {
    const errors = errorsFor((input) =>
      translate(input, "yo", {
        greeting: "Bawo {name, number}",
        count: "{count, plural, one {# a} other {# b}}"
      })
    );

    expect(errors).toContain('yo: "shell.greeting" uses "name" as number, en uses argument');
  });

  it("requires an other branch for plural and select and rejects unknown plural categories", () => {
    expect(
      errorsFor((input) =>
        translate(input, "ig", { greeting: "Nno {name}", count: "{count, plural, one {# a}}" })
      ).some((error) => error.includes('plural "count" has no "other" branch'))
    ).toBe(true);
    expect(() => describeMessage("{n, select, a {A}}")).not.toThrow();
    expect(describeMessage("{n, select, a {A}}").problems).toContain(
      'select "n" has no "other" branch'
    );
    expect(describeMessage("{n, plural, few {a} many {b} other {c}}").problems).toEqual([]);
    expect(describeMessage("{n, plural, zilch {a} other {c}}").problems).toContain(
      'plural "n" has unknown branch "zilch"'
    );
    expect(describeMessage("{n, plural, =0 {none} other {some}}").problems).toEqual([]);
  });

  it("requires the same select branches and finds variables nested in branches and tags", () => {
    const errors = errorsFor((input) =>
      translate(
        input,
        "ha",
        { greeting: "Sannu {name}", count: "{count, plural, one {# a} other {# b}}" },
        { title: "T", kind: "{kind, select, a {A} c {C} other {D}}" }
      )
    );

    expect(
      errors.some((error) =>
        error.includes('select "kind" has branches [a,c,other], en has [a,b,other]')
      )
    ).toBe(true);

    const nested = describeMessage("<b>{who}</b> {n, plural, one {{item}} other {# x}}");
    expect([...nested.variables.entries()].toSorted()).toEqual([
      ["b", "tag"],
      ["item", "argument"],
      ["n", "plural"],
      ["who", "argument"]
    ]);
    expect(describeMessage("{x} {x, number}").problems).toContain(
      'variable "x" is used as both argument and number'
    );
  });
});

describe("translation status", () => {
  it("rejects translated text under a pending status", () => {
    const errors = errorsFor((input) => {
      (input.catalogues["ha"]?.["landing"] as Json)["title"] = "Taken";
    });

    expect(errors).toContain(
      "status: ha.landing is pending but has translated text; set a status and reviewer"
    );
  });

  it("requires complete text, a reviewer, and a date when a domain is not pending", () => {
    const partial = errorsFor((input) => {
      input.catalogues["ha"] = {
        shell: { greeting: "Sannu {name}", count: null },
        landing: { title: "T", kind: "{kind, select, a {A} b {B} other {C}}" }
      };
      const locales = input.status["locales"] as Record<string, Json>;
      locales["ha"] = {
        shell: { status: "machine_assisted", reviewer: "tester", reviewedOn: "2026-09-20" },
        landing: { status: "machine_assisted" }
      };
    });

    expect(partial).toContain("status: ha.shell is machine_assisted but 1 key(s) are still null");
    expect(partial).toContain("status: ha.landing is machine_assisted and needs a named reviewer");
    expect(partial).toContain(
      "status: ha.landing is machine_assisted and needs a reviewedOn date (YYYY-MM-DD)"
    );
  });

  it("requires a valid status value, matching domains, and a reviewed English source", () => {
    expect(
      errorsFor(
        (input) =>
          (((input.status["locales"] as Json)["ha"] as Json)["shell"] = { status: "approved" })
      )
    ).toContain("status: ha.shell needs a status of reviewed, machine_assisted, or pending");
    expect(
      errorsFor((input) => delete (input.status["domains"] as Json)["landing"]).some((error) =>
        error.includes("must equal catalogue domains")
      )
    ).toBe(true);
    expect(
      errorsFor(
        (input) =>
          (((input.status["locales"] as Json)["en"] as Json)["shell"] = { status: "pending" })
      )
    ).toContain("status: en.shell is the source and must be reviewed");
    expect(errorsFor((input) => delete (input.status["locales"] as Json)["yo"])).toContain(
      'status: locale "yo" is missing'
    );
    expect(errorsFor((input) => (input.status["domains"] = undefined))).toContain(
      "status: must have `domains` and `locales` objects"
    );
    expect(
      errorsFor((input) => ((input.status["domains"] as Json)["shell"] = { critical: "yes" }))
    ).toContain('status: domain "shell" needs a boolean "critical"');
  });
});
