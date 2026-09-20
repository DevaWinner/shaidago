import { LIMITS } from "@/lib/report/flow";

/**
 * Client-side preparation of an attachment. It exists for the person's benefit: to remove hidden
 * location and camera details from a photo before it leaves the device, and to reject a file that
 * cannot be accepted without uploading it. It is NOT the security boundary. The server sniffs the
 * real type again, decodes with limits, removes metadata again, scans where configured, and keeps
 * only its own sanitised copy. A file this module passes can still be rejected there.
 */

export type SniffedType = "image/jpeg" | "image/png" | "image/webp" | "application/pdf";

export const MAX_PIXELS = 40_000_000;
export const MAX_SIDE = 2560;

export type PrepareFailure =
  "unsupported" | "tooLarge" | "mismatch" | "tooManyPixels" | "failed" | "empty";

export type PreparedFile = Readonly<{
  file: File;
  kind: "image" | "pdf";
  /** True when the image was re-encoded here, which drops EXIF, IPTC, and XMP. */
  cleaned: boolean;
}>;

export type PrepareResult =
  Readonly<{ ok: true; prepared: PreparedFile }> | Readonly<{ ok: false; reason: PrepareFailure }>;

function startsWith(bytes: Uint8Array, signature: readonly number[], offset = 0): boolean {
  return signature.every((value, index) => bytes[offset + index] === value);
}

/** The real type from the first bytes, never from the file name or the browser's guess. */
export function sniffType(bytes: Uint8Array): SniffedType | undefined {
  if (startsWith(bytes, [0xff, 0xd8, 0xff])) {
    return "image/jpeg";
  }
  if (startsWith(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) {
    return "image/png";
  }
  if (
    startsWith(bytes, [0x52, 0x49, 0x46, 0x46]) &&
    startsWith(bytes, [0x57, 0x45, 0x42, 0x50], 8)
  ) {
    return "image/webp";
  }
  if (startsWith(bytes, [0x25, 0x50, 0x44, 0x46, 0x2d])) {
    return "application/pdf";
  }

  return undefined;
}

function u16(bytes: Uint8Array, at: number): number {
  return ((bytes[at] ?? 0) << 8) | (bytes[at + 1] ?? 0);
}

function u32(bytes: Uint8Array, at: number): number {
  return (u16(bytes, at) * 65536 + u16(bytes, at + 2)) >>> 0;
}

function le24(bytes: Uint8Array, at: number): number {
  return (bytes[at] ?? 0) | ((bytes[at + 1] ?? 0) << 8) | ((bytes[at + 2] ?? 0) << 16);
}

function jpegSize(bytes: Uint8Array): { width: number; height: number } | undefined {
  let at = 2;

  while (at + 9 < bytes.length) {
    if (bytes[at] !== 0xff) {
      return undefined;
    }

    const marker = bytes[at + 1] ?? 0;

    if (marker === 0xff) {
      at += 1;
      continue;
    }
    // Start-of-frame markers carry the size; 0xc4, 0xc8, and 0xcc are not frames.
    if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
      return { height: u16(bytes, at + 5), width: u16(bytes, at + 7) };
    }
    at += 2 + u16(bytes, at + 2);
  }

  return undefined;
}

function webpSize(bytes: Uint8Array): { width: number; height: number } | undefined {
  const chunk = String.fromCharCode(...bytes.slice(12, 16));

  if (chunk === "VP8X") {
    return { width: le24(bytes, 24) + 1, height: le24(bytes, 27) + 1 };
  }
  if (chunk === "VP8L") {
    const bits =
      (bytes[21] ?? 0) |
      ((bytes[22] ?? 0) << 8) |
      ((bytes[23] ?? 0) << 16) |
      ((bytes[24] ?? 0) << 24);

    return { width: (bits & 0x3fff) + 1, height: ((bits >>> 14) & 0x3fff) + 1 };
  }
  if (chunk === "VP8 ") {
    return {
      width: ((bytes[26] ?? 0) | ((bytes[27] ?? 0) << 8)) & 0x3fff,
      height: ((bytes[28] ?? 0) | ((bytes[29] ?? 0) << 8)) & 0x3fff
    };
  }

  return undefined;
}

/** Pixel size read from the header alone, so an oversized image is refused before any decoding. */
export function imageSize(
  bytes: Uint8Array,
  type: Exclude<SniffedType, "application/pdf">
): { width: number; height: number } | undefined {
  if (type === "image/png") {
    return bytes.length >= 24 ? { width: u32(bytes, 16), height: u32(bytes, 20) } : undefined;
  }

  return type === "image/jpeg" ? jpegSize(bytes) : webpSize(bytes);
}

const EXTENSIONS: Readonly<Record<SniffedType, string>> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
  "application/pdf": "pdf"
};

export type Decoder = (
  file: File,
  size: { width: number; height: number },
  type: Exclude<SniffedType, "application/pdf">,
  signal: AbortSignal | undefined
) => Promise<Blob>;

/** Decodes with the browser's orientation applied, scales down, and re-encodes with no metadata. */
export const browserDecoder: Decoder = async (file, size, type, signal) => {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });

  try {
    if (signal?.aborted === true) {
      throw new DOMException("aborted", "AbortError");
    }

    const scale = Math.min(
      1,
      MAX_SIDE / Math.max(bitmap.width, bitmap.height, size.width, size.height)
    );
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement("canvas");

    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");

    if (context === null) {
      throw new Error("no canvas");
    }
    context.drawImage(bitmap, 0, 0, width, height);

    return await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob(
        (blob) => (blob === null ? reject(new Error("encode failed")) : resolve(blob)),
        type,
        0.85
      );
    });
  } finally {
    bitmap.close();
  }
};

/**
 * Checks and prepares one file. `index` is the file's 1-based place, used only to name the sanitised
 * copy: the original name is never sent, because a file name can identify a person or a place.
 */
export async function prepareFile(
  file: File,
  index: number,
  options: { decoder?: Decoder; signal?: AbortSignal } = {}
): Promise<PrepareResult> {
  if (file.size === 0) {
    return { ok: false, reason: "empty" };
  }
  if (file.size > LIMITS.fileBytes) {
    return { ok: false, reason: "tooLarge" };
  }

  const head = new Uint8Array(await file.slice(0, 64 * 1024).arrayBuffer());
  const type = sniffType(head);

  if (type === undefined) {
    return { ok: false, reason: "unsupported" };
  }
  if (file.type !== "" && file.type !== type) {
    return { ok: false, reason: "mismatch" };
  }

  const name = `attachment-${index}.${EXTENSIONS[type]}`;

  if (type === "application/pdf") {
    return {
      ok: true,
      prepared: { file: new File([file], name, { type }), kind: "pdf", cleaned: false }
    };
  }

  const size = imageSize(head, type);

  if (size === undefined || size.width < 1 || size.height < 1) {
    return { ok: false, reason: "failed" };
  }
  if (size.width * size.height > MAX_PIXELS) {
    return { ok: false, reason: "tooManyPixels" };
  }

  try {
    const blob = await (options.decoder ?? browserDecoder)(file, size, type, options.signal);

    // An encoder can fall back to another format; only the three accepted types leave here.
    const outType = blob.type === "" ? type : blob.type;

    if (!["image/jpeg", "image/png", "image/webp"].includes(outType)) {
      return { ok: false, reason: "failed" };
    }
    if (blob.size > LIMITS.fileBytes || blob.size === 0) {
      return { ok: false, reason: blob.size === 0 ? "failed" : "tooLarge" };
    }

    return {
      ok: true,
      prepared: {
        file: new File([blob], `attachment-${index}.${EXTENSIONS[outType as SniffedType]}`, {
          type: outType
        }),
        kind: "image",
        cleaned: true
      }
    };
  } catch {
    return { ok: false, reason: "failed" };
  }
}
