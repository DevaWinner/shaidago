import { describe, expect, it } from "vitest";

import { LIMITS } from "@/lib/report/flow";
import {
  MAX_PIXELS,
  imageSize,
  prepareFile,
  sniffType,
  type Decoder
} from "@/lib/report/image-prep";

const bytes = (...values: number[]) => new Uint8Array(values);
const pad = (values: number[], length: number) =>
  Uint8Array.from({ length }, (_, index) => values[index] ?? 0);

function jpeg(width: number, height: number): Uint8Array {
  // SOI, an APP1 (Exif) segment, then a baseline frame header.
  return Uint8Array.from([
    0xff,
    0xd8,
    0xff,
    0xe1,
    0x00,
    0x08,
    0x45,
    0x78,
    0x69,
    0x66,
    0x00,
    0x00,
    0xff,
    0xc0,
    0x00,
    0x11,
    0x08,
    height >> 8,
    height & 255,
    width >> 8,
    width & 255,
    3,
    1,
    0x22,
    0,
    2,
    0x11,
    1,
    3,
    0x11,
    1
  ]);
}

function png(width: number, height: number): Uint8Array {
  return Uint8Array.from([
    0x89,
    0x50,
    0x4e,
    0x47,
    0x0d,
    0x0a,
    0x1a,
    0x0a,
    0,
    0,
    0,
    13,
    0x49,
    0x48,
    0x44,
    0x52,
    width >>> 24,
    (width >> 16) & 255,
    (width >> 8) & 255,
    width & 255,
    height >>> 24,
    (height >> 16) & 255,
    (height >> 8) & 255,
    height & 255,
    8,
    6,
    0,
    0,
    0
  ]);
}

function webpX(width: number, height: number): Uint8Array {
  const out = pad(
    [0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50, 0x56, 0x50, 0x38, 0x58],
    32
  );
  const w = width - 1;
  const h = height - 1;

  out.set([w & 255, (w >> 8) & 255, (w >> 16) & 255], 24);
  out.set([h & 255, (h >> 8) & 255, (h >> 16) & 255], 27);

  return out;
}

const file = (data: Uint8Array, type = "", name = "photo.jpg") =>
  new File([data as BlobPart], name, { type });
const decoder: Decoder = async (_file, _size, type) => new Blob(["cleaned"], { type });

describe("sniffType", () => {
  it("names the four accepted types from their first bytes", () => {
    expect(sniffType(jpeg(2, 2))).toBe("image/jpeg");
    expect(sniffType(png(2, 2))).toBe("image/png");
    expect(sniffType(webpX(2, 2))).toBe("image/webp");
    expect(sniffType(Uint8Array.from([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31]))).toBe(
      "application/pdf"
    );
  });

  it("does not recognise anything else, whatever the name says", () => {
    expect(sniffType(bytes(0x47, 0x49, 0x46, 0x38))).toBeUndefined();
    expect(sniffType(Uint8Array.from(Buffer.from("<svg xmlns='x'></svg>")))).toBeUndefined();
    expect(sniffType(bytes())).toBeUndefined();
  });
});

describe("imageSize", () => {
  it("reads the pixel size from the header alone", () => {
    expect(imageSize(jpeg(300, 200), "image/jpeg")).toEqual({ width: 300, height: 200 });
    expect(imageSize(png(640, 480), "image/png")).toEqual({ width: 640, height: 480 });
    expect(imageSize(webpX(800, 600), "image/webp")).toEqual({ width: 800, height: 600 });
  });

  it("returns nothing when the header is truncated or malformed", () => {
    expect(imageSize(bytes(0xff, 0xd8, 0xff), "image/jpeg")).toBeUndefined();
    expect(imageSize(png(1, 1).slice(0, 10), "image/png")).toBeUndefined();
    expect(
      imageSize(Uint8Array.from([0xff, 0xd8, 0x00, 0, 0, 0, 0, 0, 0, 0, 0, 0]), "image/jpeg")
    ).toBeUndefined();
  });
});

describe("prepareFile", () => {
  it("re-saves an image under a neutral name so no hidden details or file name are kept", async () => {
    const result = await prepareFile(file(jpeg(300, 200), "image/jpeg", "Home-Lekki-GPS.jpg"), 2, {
      decoder
    });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.prepared).toMatchObject({ kind: "image", cleaned: true });
      expect(result.prepared.file.name).toBe("attachment-2.jpg");
      expect(await result.prepared.file.text()).toBe("cleaned");
    }
  });

  it("passes a PDF through unchanged, honestly marked as not cleaned here, with a neutral name", async () => {
    const pdf = Uint8Array.from(Buffer.from("%PDF-1.7 body"));
    const result = await prepareFile(file(pdf, "application/pdf", "Secret name.pdf"), 1);

    expect(result.ok && result.prepared).toMatchObject({ kind: "pdf", cleaned: false });
    expect(result.ok && result.prepared.file.name).toBe("attachment-1.pdf");
  });

  it.each([
    ["an empty file", new File([], "a.jpg", { type: "image/jpeg" }), "empty"],
    [
      "an unsupported file",
      file(Uint8Array.from(Buffer.from("GIF89a....")), "image/gif"),
      "unsupported"
    ],
    ["a file whose type disagrees with its bytes", file(png(4, 4), "image/jpeg"), "mismatch"],
    ["an image too large in pixels", file(png(9000, 9000), "image/png"), "tooManyPixels"],
    [
      "an image with an unreadable header",
      file(bytes(0xff, 0xd8, 0xff, 0, 0), "image/jpeg"),
      "failed"
    ]
  ])("refuses %s before decoding", async (_name, input, reason) => {
    expect(await prepareFile(input, 1, { decoder })).toEqual({ ok: false, reason });
  });

  it("refuses a file over the size limit without reading it", async () => {
    const big = file(jpeg(4, 4), "image/jpeg");

    Object.defineProperty(big, "size", { value: LIMITS.fileBytes + 1 });
    expect(await prepareFile(big, 1, { decoder })).toEqual({ ok: false, reason: "tooLarge" });
    expect(MAX_PIXELS).toBeLessThan(9000 * 9000);
  });

  it("fails safely when the browser cannot decode, or encodes to something else", async () => {
    const image = file(jpeg(10, 10), "image/jpeg");

    expect(
      await prepareFile(image, 1, {
        decoder: async () => {
          throw new Error("bad image");
        }
      })
    ).toEqual({ ok: false, reason: "failed" });
    expect(
      await prepareFile(image, 1, { decoder: async () => new Blob(["x"], { type: "image/gif" }) })
    ).toEqual({ ok: false, reason: "failed" });
    expect(
      await prepareFile(image, 1, { decoder: async () => new Blob([], { type: "image/png" }) })
    ).toEqual({
      ok: false,
      reason: "failed"
    });
  });

  it("uses the encoder's own type for the name when it fell back to another allowed format", async () => {
    const result = await prepareFile(file(webpX(10, 10), "image/webp", "a.webp"), 3, {
      decoder: async () => new Blob(["x"], { type: "image/png" })
    });

    expect(result.ok && result.prepared.file.name).toBe("attachment-3.png");
  });

  it("refuses a result larger than the limit", async () => {
    const huge = { type: "image/jpeg", size: LIMITS.fileBytes + 1 } as Blob;

    expect(
      await prepareFile(file(jpeg(10, 10), "image/jpeg"), 1, { decoder: async () => huge })
    ).toEqual({ ok: false, reason: "tooLarge" });
  });
});
