import { describe, expect, it } from "vitest";

import { EMPTY_FORM, type ReportForm } from "@/lib/report/flow";
import { buildBody, parseReceipt, payloadSignature } from "@/lib/report/submit";

const base: ReportForm = {
  ...EMPTY_FORM,
  category: "unsafe_construction",
  description: "  A wall is leaning by the road.  "
};
const file = (name: string, size = 3) =>
  new File([new Uint8Array(size)], name, { type: "image/png" });

describe("buildBody", () => {
  it("sends only the fields an anonymous report needs", () => {
    const body = buildBody({ slug: "p-1", form: base, files: [] });

    expect([...body.keys()]).toEqual(["project_slug", "concern_category", "description"]);
    expect(body.get("description")).toBe("A wall is leaning by the road.");
  });

  it("adds contact fields only for the contact mode, and handle fields only for the handle mode", () => {
    const contact = buildBody({
      slug: "p-1",
      form: { ...base, mode: "contact", contactChannel: "email", contactValue: " a@example.org " },
      files: []
    });
    const handle = buildBody({
      slug: "p-1",
      form: { ...base, mode: "handle", handle: " h ", passphrase: "six words here" },
      files: []
    });

    expect(contact.get("contact_channel")).toBe("email");
    expect(contact.get("contact_value")).toBe("a@example.org");
    expect(contact.has("reporter_handle")).toBe(false);
    expect(handle.get("reporter_handle")).toBe("h");
    expect(handle.get("reporter_passphrase")).toBe("six words here");
    expect(handle.has("contact_value")).toBe(false);
  });

  it("appends each file as an attachment under its neutral name", () => {
    const body = buildBody({
      slug: "p-1",
      form: base,
      files: [file("attachment-1.png"), file("attachment-2.png")]
    });
    const parts = body.getAll("attachments") as File[];

    expect(parts.map((part) => part.name)).toEqual(["attachment-1.png", "attachment-2.png"]);
  });
});

describe("payloadSignature", () => {
  const input = { slug: "p-1", form: base, files: [file("a.png")] };

  it("is stable for the same reviewed report and changes when anything sent changes", () => {
    expect(payloadSignature(input)).toBe(payloadSignature({ ...input }));
    expect(payloadSignature({ ...input, slug: "p-2" })).not.toBe(payloadSignature(input));
    expect(
      payloadSignature({
        ...input,
        form: { ...base, description: "A different description here." }
      })
    ).not.toBe(payloadSignature(input));
    expect(payloadSignature({ ...input, files: [file("a.png", 9)] })).not.toBe(
      payloadSignature(input)
    );
    expect(
      payloadSignature({
        ...input,
        form: { ...base, mode: "handle", handle: "h", passphrase: "p" }
      })
    ).not.toBe(payloadSignature(input));
  });

  it("ignores surrounding whitespace, as the body does", () => {
    expect(
      payloadSignature({ ...input, form: { ...base, description: base.description.trim() } })
    ).toBe(payloadSignature(input));
  });
});

describe("parseReceipt", () => {
  const good = {
    attachments: [{ kept: true, position: 0, reason: null }],
    contact_saved: false,
    next_steps: ["save_tracking_code"],
    published: false,
    status: "received",
    tracking_code: "SG-DEMO-0001"
  };

  it("accepts the documented receipt and records whether a handle was used", () => {
    expect(parseReceipt(good, true)).toEqual({
      trackingCode: "SG-DEMO-0001",
      contactSaved: false,
      attachments: [{ position: 0, kept: true, reason: null }],
      nextSteps: ["save_tracking_code"],
      handleUsed: true
    });
  });

  it.each([
    ["a non-object", "x"],
    ["no code", { ...good, tracking_code: "" }],
    ["an over-long code", { ...good, tracking_code: "x".repeat(201) }],
    ["a published report", { ...good, published: true }],
    ["another status", { ...good, status: "closed" }],
    ["a bad contact flag", { ...good, contact_saved: "no" }],
    ["too many attachments", { ...good, attachments: Array(4).fill(good.attachments[0]) }],
    [
      "a malformed attachment",
      { ...good, attachments: [{ kept: "yes", position: 0, reason: null }] }
    ],
    ["a non-array attachment list", { ...good, attachments: null }],
    ["bad next steps", { ...good, next_steps: [1] }]
  ])("rejects %s", (_name, value) => {
    expect(parseReceipt(value, false)).toBeUndefined();
  });
});
