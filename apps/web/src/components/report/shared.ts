import type { Messages } from "@/i18n/catalogue";
import { formatMessageLite } from "@/lib/directory/format-lite";
import { LIMITS, type ErrorKey } from "@/lib/report/flow";

export type Copy = Messages["report"];

export const IDS = {
  category: "report-category",
  description: "report-description",
  contactChannel: "report-contact-channel",
  contactValue: "report-contact-value",
  handle: "report-handle",
  passphrase: "report-passphrase"
} as const;

/** The message for a step error; a server-reported error uses the same wording. */
export function errorMessage(copy: Copy, key: ErrorKey): string {
  const text = copy.errors;

  return formatMessageLite(
    {
      category: text.category,
      descriptionRequired: text.descriptionRequired,
      descriptionShort: text.descriptionShort,
      descriptionLong: text.descriptionLong,
      contact: text.contact,
      channel: text.channel,
      handle: text.handle,
      passphrase: text.passphrase
    }[key],
    { min: LIMITS.descriptionMin, max: LIMITS.descriptionMax }
  );
}
