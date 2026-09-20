import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import {
  LOCALES,
  checkCatalogues,
  describeMessage,
  pendingKeys
} from "../../scripts/messages-parity.mjs";
import { REVIEWED_LOCALES } from "@/i18n/routing";

type Json = Record<string, unknown>;
// Domains added after the maintainer's translation pass: `null` in ha, ig, and yo until the end.
const PENDING_DOMAINS = [
  "problems",
  "language",
  "directory",
  "home",
  "project",
  "source",
  "trust",
  "qa",
  "report",
  "track",
  "handle",
  "reviewer",
  "discovery"
];
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
    const catalogues = Object.fromEntries([...LOCALES].map((locale) => [locale, read(locale)]));

    expect(LOCALES).toEqual(["en", "ha", "ig", "yo"]);
    expect(checkCatalogues({ catalogues, status: read("status") })).toEqual([]);
  });

  it("list the keys still waiting for the maintainer's translation pass, identically for every locale", () => {
    const catalogues = Object.fromEntries([...LOCALES].map((locale) => [locale, read(locale)]));
    const pending = pendingKeys({ catalogues }) as Record<string, string[]>;

    expect(pending["ha"]).toEqual(pending["ig"]);
    expect(pending["ha"]).toEqual(pending["yo"]);
    expect(pending["ha"]).toContain("recovery.fatal.title");
    expect(
      pending["ha"]?.every(
        (key) =>
          key === "recovery.fatal.title" ||
          key.startsWith("problems.") ||
          key.startsWith("language.") ||
          key.startsWith("directory.") ||
          key.startsWith("home.") ||
          key.startsWith("project.") ||
          key.startsWith("source.") ||
          key.startsWith("trust.") ||
          key.startsWith("qa.") ||
          key.startsWith("report.") ||
          key.startsWith("track.") ||
          key.startsWith("handle.") ||
          key.startsWith("reviewer.") ||
          key.startsWith("discovery.")
      )
    ).toBe(true);
    expect((read("status") as { pendingKeysAllowed?: boolean }).pendingKeysAllowed).toBe(true);
  });

  it("mark every served domain reviewed with a named reviewer and date, and keep the domains added since the translation pass pending", () => {
    const status = read("status") as {
      domains: Record<string, { critical: boolean }>;
      locales: Record<
        string,
        Record<string, { status: string; reviewer?: string; reviewedOn?: string }>
      >;
    };

    for (const locale of LOCALES) {
      for (const [domain, record] of Object.entries(status.locales[locale] ?? {})) {
        if (PENDING_DOMAINS.includes(domain) && locale !== "en") {
          // New keys are added as null for the maintainer's end-of-build translation pass.
          expect(record.status, `${locale}.${domain}`).toBe("pending");
          expect(status.domains[domain]?.critical, domain).toBe(false);
          continue;
        }
        expect(record.status, `${locale}.${domain}`).toBe("reviewed");
        expect(record.reviewer, `${locale}.${domain}`).toMatch(/\S/);
        expect(record.reviewedOn, `${locale}.${domain}`).toBe("2026-09-20");
      }
    }
    expect([...REVIEWED_LOCALES]).toEqual(["en", "ha", "ig", "yo"]);
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

  it("allows null keys in a reviewed domain only while the build-phase switch is on, and lists them", () => {
    const gappy = (input: ReturnType<typeof fixture>, allowed: boolean | undefined) => {
      input.catalogues["ha"] = {
        shell: { greeting: "Sannu {name}", count: null },
        landing: { title: "T", kind: "{kind, select, a {A} b {B} other {C}}" }
      };
      const record = { status: "reviewed", reviewer: "tester", reviewedOn: "2026-09-20" };
      (input.status["locales"] as Record<string, Json>)["ha"] = { shell: record, landing: record };
      if (allowed !== undefined) {
        input.status["pendingKeysAllowed"] = allowed;
      }
    };

    expect(errorsFor((input) => gappy(input, true))).toEqual([]);
    expect(errorsFor((input) => gappy(input, false))).toContain(
      "status: ha.shell is reviewed but 1 key(s) are still null"
    );
    expect(errorsFor((input) => gappy(input, undefined))).toContain(
      "status: ha.shell is reviewed but 1 key(s) are still null"
    );

    const input = fixture();
    gappy(input, true);
    expect(pendingKeys(input)).toEqual({
      ha: ["shell.count"],
      ig: ["shell.greeting", "shell.count", "landing.title", "landing.kind"],
      yo: ["shell.greeting", "shell.count", "landing.title", "landing.kind"]
    });
  });

  it("still requires a reviewer and date for a reviewed domain that has pending keys", () => {
    const errors = errorsFor((input) => {
      input.status["pendingKeysAllowed"] = true;
      input.catalogues["ha"] = {
        shell: { greeting: "Sannu {name}", count: null },
        landing: { title: "T", kind: "{kind, select, a {A} b {B} other {C}}" }
      };
      (input.status["locales"] as Record<string, Json>)["ha"] = {
        shell: { status: "reviewed" },
        landing: { status: "reviewed" }
      };
    });

    expect(errors).toContain("status: ha.shell is reviewed and needs a named reviewer");
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
