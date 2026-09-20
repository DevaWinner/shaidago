import { readBrowserProblem, networkProblem } from "@/lib/problems/browser-problem";
import type { SafeProblem } from "@/lib/problems/problem-messages";
import type { ReportForm } from "@/lib/report/flow";
import type { Receipt, ReceiptAttachment } from "@/lib/report/receipt-store";

/**
 * Sends one report through the same-origin route handler as a multipart body. The browser never
 * chooses the destination: it is a fixed path. Values are never logged or copied anywhere else.
 * `XMLHttpRequest` is used instead of `fetch` only because `fetch` cannot report upload progress.
 */

export const SUBMIT_URL = "/api/reports";

export type SubmitInput = Readonly<{ slug: string; form: ReportForm; files: readonly File[] }>;

export type SubmitOutcome =
  | Readonly<{ kind: "received"; receipt: Receipt; replayed: boolean }>
  | Readonly<{ kind: "problem"; problem: SafeProblem }>
  | Readonly<{ kind: "network" }>
  | Readonly<{ kind: "aborted" }>;

/** Only the fields the chosen identity mode needs are sent; the others do not exist in the body. */
export function buildBody(input: SubmitInput): FormData {
  const body = new FormData();
  const { form } = input;

  body.set("project_slug", input.slug);
  body.set("concern_category", form.category);
  body.set("description", form.description.trim());

  if (form.mode === "contact") {
    body.set("contact_channel", form.contactChannel);
    body.set("contact_value", form.contactValue.trim());
  }
  if (form.mode === "handle") {
    body.set("reporter_handle", form.handle.trim());
    body.set("reporter_passphrase", form.passphrase);
  }
  for (const file of input.files) {
    body.append("attachments", file, file.name);
  }

  return body;
}

/**
 * A fingerprint of what would be sent. The idempotency key is reused only while this is unchanged,
 * so retrying the same reviewed report cannot create a second one, and an edited report is a new
 * intent with a new key. It holds no secret: it is compared in memory and never sent.
 */
export function payloadSignature(input: SubmitInput): string {
  const { form } = input;

  return JSON.stringify([
    input.slug,
    form.category,
    form.description.trim(),
    form.mode,
    form.contactChannel,
    form.contactValue.trim(),
    form.handle.trim(),
    form.passphrase,
    input.files.map((file) => [file.size, file.lastModified, file.type])
  ]);
}

function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseAttachment(value: unknown): ReceiptAttachment | undefined {
  if (
    !isRecord(value) ||
    !Number.isInteger(value["position"]) ||
    typeof value["kept"] !== "boolean" ||
    !(value["reason"] === null || typeof value["reason"] === "string")
  ) {
    return undefined;
  }

  return {
    position: Number(value["position"]),
    kept: value["kept"],
    reason: value["reason"]
  };
}

/** A receipt is trusted only in the documented shape; anything else is an unreadable response. */
export function parseReceipt(value: unknown, handleUsed: boolean): Receipt | undefined {
  if (
    !isRecord(value) ||
    typeof value["tracking_code"] !== "string" ||
    value["tracking_code"] === "" ||
    value["tracking_code"].length > 200 ||
    value["status"] !== "received" ||
    value["published"] !== false ||
    typeof value["contact_saved"] !== "boolean" ||
    !Array.isArray(value["attachments"]) ||
    value["attachments"].length > 3 ||
    !Array.isArray(value["next_steps"]) ||
    !(value["next_steps"] as unknown[]).every((step) => typeof step === "string")
  ) {
    return undefined;
  }

  const attachments: ReceiptAttachment[] = [];

  for (const item of value["attachments"] as unknown[]) {
    const parsed = parseAttachment(item);

    if (parsed === undefined) {
      return undefined;
    }
    attachments.push(parsed);
  }

  return {
    trackingCode: value["tracking_code"],
    contactSaved: value["contact_saved"],
    attachments,
    nextSteps: value["next_steps"] as string[],
    handleUsed
  };
}

function responseHeaders(xhr: XMLHttpRequest): Headers {
  const headers = new Headers();

  for (const line of xhr.getAllResponseHeaders().trim().split(/\r?\n/)) {
    const at = line.indexOf(":");

    if (at > 0) {
      try {
        headers.append(line.slice(0, at).trim(), line.slice(at + 1).trim());
      } catch {
        // A header the runtime refuses is not one this code reads.
      }
    }
  }

  return headers;
}

export function submitReport(options: {
  input: SubmitInput;
  idempotencyKey: string;
  locale: string;
  onProgress: (fraction: number) => void;
  signal: AbortSignal;
}): Promise<SubmitOutcome> {
  return new Promise((resolve) => {
    if (options.signal.aborted) {
      resolve({ kind: "aborted" });
      return;
    }

    const xhr = new XMLHttpRequest();

    xhr.open("POST", SUBMIT_URL);
    xhr.setRequestHeader("Accept", "application/json");
    xhr.setRequestHeader("Idempotency-Key", options.idempotencyKey);
    xhr.setRequestHeader("X-Shaidago-Locale", options.locale);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) {
        options.onProgress(Math.min(1, event.loaded / event.total));
      }
    };
    options.signal.addEventListener("abort", () => xhr.abort(), { once: true });
    xhr.onabort = () => resolve({ kind: "aborted" });
    xhr.onerror = () => resolve({ kind: "network" });
    xhr.ontimeout = () => resolve({ kind: "network" });
    xhr.onload = () => {
      const headers = responseHeaders(xhr);

      void (async () => {
        if (xhr.status === 201) {
          let parsed: unknown;

          try {
            parsed = JSON.parse(xhr.responseText);
          } catch {
            parsed = undefined;
          }

          const receipt = parseReceipt(parsed, options.input.form.mode === "handle");

          resolve(
            receipt === undefined
              ? {
                  kind: "problem",
                  problem: {
                    ...networkProblem(),
                    code: "internal_error",
                    status: 201,
                    requestId: headers.get("X-Request-Id") ?? undefined
                  }
                }
              : {
                  kind: "received",
                  receipt,
                  replayed: headers.get("Idempotency-Replayed") === "true"
                }
          );
          return;
        }

        resolve({
          kind: "problem",
          problem: await readBrowserProblem(
            new Response(xhr.responseText, {
              status: xhr.status >= 200 ? xhr.status : 500,
              headers
            })
          )
        });
      })();
    };

    xhr.send(buildBody(options.input));
  });
}
