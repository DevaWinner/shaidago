import { describe, expect, it } from "vitest";

import {
  EMPTY_FORM,
  STEPS,
  firstInvalidStep,
  hasContent,
  nextStep,
  previousStep,
  stepForApiField,
  stepForField,
  validateStep,
  withMode,
  type ReportForm
} from "@/lib/report/flow";

const valid: ReportForm = {
  ...EMPTY_FORM,
  category: "unsafe_construction",
  description: "The wall by the road is cracked and leaning."
};

describe("step order", () => {
  it("moves forward and back inside the five steps and stops at both ends", () => {
    expect([...STEPS]).toEqual(["notice", "observation", "evidence", "anonymity", "review"]);
    expect(nextStep("notice")).toBe("observation");
    expect(nextStep("review")).toBe("review");
    expect(previousStep("review")).toBe("anonymity");
    expect(previousStep("notice")).toBe("notice");
  });
});

describe("validateStep", () => {
  it("requires a category and a long enough description on the observation step", () => {
    expect(validateStep("observation", EMPTY_FORM).map((error) => error.key)).toEqual([
      "category",
      "descriptionRequired"
    ]);
    expect(
      validateStep("observation", { ...valid, description: "  short  " }).map((error) => error.key)
    ).toEqual(["descriptionShort"]);
    expect(
      validateStep("observation", { ...valid, description: "x".repeat(8001) }).map(
        (error) => error.key
      )
    ).toEqual(["descriptionLong"]);
    expect(validateStep("observation", valid)).toEqual([]);
  });

  it("asks nothing of the notice, evidence, and review steps", () => {
    for (const step of ["notice", "evidence", "review"] as const) {
      expect(validateStep(step, EMPTY_FORM)).toEqual([]);
    }
  });

  it("asks only for what the chosen identity mode needs", () => {
    expect(validateStep("anonymity", valid)).toEqual([]);
    expect(
      validateStep("anonymity", { ...valid, mode: "contact" }).map((error) => error.field)
    ).toEqual(["contactChannel", "contactValue"]);
    expect(
      validateStep("anonymity", {
        ...valid,
        mode: "contact",
        contactChannel: "email",
        contactValue: "  "
      }).map((error) => error.field)
    ).toEqual(["contactValue"]);
    expect(
      validateStep("anonymity", { ...valid, mode: "handle" }).map((error) => error.field)
    ).toEqual(["handle", "passphrase"]);
    expect(
      validateStep("anonymity", { ...valid, mode: "handle", handle: "h", passphrase: "p" })
    ).toEqual([]);
  });

  it("finds the earliest broken step, so a late failure returns to where it can be fixed", () => {
    expect(firstInvalidStep(EMPTY_FORM)).toBe("observation");
    expect(firstInvalidStep({ ...valid, mode: "handle" })).toBe("anonymity");
    expect(firstInvalidStep(valid)).toBeUndefined();
  });
});

describe("withMode", () => {
  it("deletes the other modes' values the moment the mode changes", () => {
    const filled: ReportForm = {
      ...valid,
      mode: "contact",
      contactChannel: "email",
      contactValue: "a@example.org",
      handle: "old",
      passphrase: "old secret"
    };
    const anonymous = withMode(filled, "anonymous");

    expect(anonymous).toMatchObject({
      mode: "anonymous",
      contactChannel: "",
      contactValue: "",
      handle: "",
      passphrase: ""
    });
    expect(withMode(filled, "contact")).toMatchObject({
      contactValue: "a@example.org",
      handle: ""
    });
    expect(
      withMode({ ...filled, mode: "handle", handle: "h", passphrase: "p" }, "handle")
    ).toMatchObject({
      handle: "h",
      passphrase: "p",
      contactValue: ""
    });
    // The description and category are never touched by a mode change.
    expect(anonymous.description).toBe(valid.description);
  });
});

describe("field and step mapping", () => {
  it("maps API field paths to the step that owns them", () => {
    expect(stepForApiField("body.description")).toBe("observation");
    expect(stepForApiField("concern_category")).toBe("observation");
    expect(stepForApiField("body.attachments.0")).toBe("evidence");
    expect(stepForApiField("body.contact_value")).toBe("anonymity");
    expect(stepForApiField("body.reporter_passphrase")).toBe("anonymity");
    expect(stepForApiField("body.something_else")).toBeUndefined();
    expect(stepForField("handle")).toBe("anonymity");
    expect(stepForField("category")).toBe("observation");
  });

  it("knows when leaving would lose something", () => {
    expect(hasContent(EMPTY_FORM, 0)).toBe(false);
    expect(hasContent(EMPTY_FORM, 1)).toBe(true);
    expect(hasContent({ ...EMPTY_FORM, category: "other_concern" }, 0)).toBe(true);
    expect(hasContent({ ...EMPTY_FORM, passphrase: "x" }, 0)).toBe(true);
    expect(hasContent({ ...EMPTY_FORM, handle: "h" }, 0)).toBe(true);
    expect(hasContent({ ...EMPTY_FORM, contactValue: "c" }, 0)).toBe(true);
    expect(hasContent({ ...EMPTY_FORM, description: "d" }, 0)).toBe(true);
  });
});
